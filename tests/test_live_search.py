# -*- coding: utf-8 -*-
"""Unit tests for multi-disciplinary real-time academic search."""
from __future__ import annotations

import pathlib
import sys
import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.sources import live_search
from app import store


class TestLiveSearch(unittest.TestCase):
    def test_empty_query(self):
        res = live_search.query_global("")
        self.assertEqual(res["papers"], [])
        self.assertEqual(res["total"], 0)
        self.assertEqual(res["pages"], 0)

    def test_chinese_subject_aliases(self):
        self.assertIn('solid-state battery', live_search._search_terms("固态电池"))
        self.assertIn('machine learning algorithm', live_search._search_terms("AI算法"))

    def test_detailed_chinese_query_requires_each_supported_concept(self):
        q = "固态电池 硫化物电解质 界面稳定性"
        terms = live_search._precise_terms(q)
        self.assertIn(" AND ", terms)
        self.assertIn("sulfide electrolyte", terms)
        self.assertGreater(live_search._topic_strength(q, terms, {
            "title": "Interfacial stability in sulfide-electrolyte solid-state batteries",
            "abstract": "",
        }, "precise"), 0)
        self.assertEqual(live_search._topic_strength(q, terms, {
            "title": "Sulfide-electrolyte solid-state batteries", "abstract": "",
        }, "precise"), 0)

    def test_classic_title_match_keeps_chinese_substring(self):
        self.assertTrue(live_search._classic_title_match(
            "基因编辑", "基因编辑", "基因编辑技术的发展", "broad"))

    def test_classic_methods_cover_multiple_disciplines(self):
        cases = [
            ("AI算法", "Scikit-learn: Machine Learning in Python", True),
            ("基因编辑", "A programmable dual-RNA-guided DNA endonuclease", False),
            ("基因编辑", "Genome editing with CRISPR-Cas9", True),
            ("量子计算", "Noisy intermediate-scale quantum computing", True),
            ("量子计算", "Quantum chemistry of water", False),
        ]
        for query, title, expected in cases:
            with self.subTest(query=query, title=title):
                terms = live_search._search_terms(query) if query == "AI算法" else query
                strength = live_search._classic_strength(
                    query, terms, {"title": title, "abstract": ""}, "broad")
                self.assertEqual(strength >= 4, expected)
        foundational = live_search._classic_strength(
            "基因编辑", '"gene editing"', {
                "title": "A Programmable Dual-RNA-Guided DNA Endonuclease",
                "primary_node": "CRISPR and Genetic Engineering",
            }, "broad")
        self.assertGreaterEqual(foundational, 4)

    @patch("app.sources.live_search._search_openalex")
    @patch("app.sources.live_search._search_terms", return_value='"gene editing"')
    def test_gene_classics_include_foundational_crispr_papers(self, _mock_terms, mock_search):
        older = f"{live_search.date.today().year - 10}-01-01"
        base = {"doi": "10.1/base", "title": "Genome editing with CRISPR",
                "abstract": "", "pub_date": older, "cited_by": 300,
                "primary_node": "CRISPR and Genetic Engineering"}
        foundation = {"doi": "10.1/foundation",
                      "title": "A Programmable Dual-RNA-Guided DNA Endonuclease",
                      "abstract": "", "pub_date": older, "cited_by": 17000,
                      "primary_node": "CRISPR and Genetic Engineering"}
        mock_search.side_effect = [
            {"papers": [base], "total": 1, "source": "openalex"},
            {"papers": [foundation], "total": 1, "source": "openalex"},
        ]
        result = live_search.query_classics("基因编辑", limit=6)
        self.assertEqual([p["doi"] for p in result["papers"]],
                         ["10.1/foundation", "10.1/base"])
        self.assertEqual(mock_search.call_args.args[0], "crispr cas9")

    @patch("app.sources.live_search._recent_citation_count")
    @patch("app.sources.live_search._search_openalex")
    def test_hot_uses_recent_citations_even_for_old_papers(self, mock_search, mock_count):
        def paper(work_id, title, published, lifetime):
            return {"doi": "10.1/" + work_id, "openalex_id": work_id,
                    "title": title, "pub_date": published, "cited_by": lifetime,
                    "journal": "Nature Physics", "abstract": "", "primary_node": ""}
        rows = [paper("W1", "Quantum computing with ions", "2012-01-01", 900),
                paper("W2", "Quantum computing with photons", "2026-09-01", 20),
                paper("W3", "Quantum chemistry with photons", "2026-09-01", 10000)]
        mock_search.return_value = {"source": "openalex", "total": 3, "papers": rows}
        mock_count.side_effect = lambda work_id, *_: {"W1": 8, "W2": 2}[work_id]
        result = live_search.query_hot("quantum computing")
        self.assertEqual([p["openalex_id"] for p in result["papers"]], ["W1", "W2"])
        self.assertEqual(result["papers"][0]["recent_citations"], 8)
        self.assertEqual(result["papers"][0]["pub_date"], "2012-01-01")
        self.assertEqual(mock_search.call_args.kwargs["sort"], "date")

    @patch("app.http_client.request")
    def test_hot_count_filters_citing_papers_by_date(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {"meta": {"count": 7}}
        self.assertEqual(live_search._recent_citation_count(
            "W123", "2026-08-26", "2026-09-24"), 7)
        filt = mock_req.call_args.kwargs["params"]["filter"]
        self.assertIn("cites:W123", filt)
        self.assertIn("from_publication_date:2026-08-26", filt)
        self.assertIn("to_publication_date:2026-09-24", filt)

    @patch("app.sources.live_search._search_openalex", return_value=None)
    def test_hot_does_not_fake_recent_citations_from_crossref(self, _mock_openalex):
        self.assertTrue(live_search.query_hot("quantum computing")["unavailable"])

    @patch("app.sources.live_search._search_openalex")
    def test_latest_ranks_papers_and_merges_repository_versions(self, mock_search):
        def paper(doi, title, journal, day, abstract=""):
            return {"doi": doi, "title": title, "journal": journal,
                    "pub_date": day, "abstract": abstract, "cited_by": 0}

        mock_search.side_effect = [
            {"source": "openalex", "total": 201, "papers": [
                paper("10.1/zenodo", "Quantum computing with neutral atoms",
                      "Zenodo", "2026-09-24"),
                paper("10.1/arxiv", "Quantum computing with neutral atoms",
                      "arXiv", "2026-09-23"),
                paper("10.1/journal", "Quantum computing with trapped ions",
                      "Nature Physics", "2026-09-22"),
                paper("10.1/noise", "Quantum chemistry with new materials",
                      "Science", "2026-09-24", "We mention quantum computing."),
            ]},
            {"source": "openalex", "total": 201, "papers": []},
        ]
        result = live_search.query_global("quantum computing", sort="date", page_size=10)
        self.assertTrue(result["ranked"])
        self.assertEqual([p["doi"] for p in result["papers"]],
                         ["10.1/arxiv", "10.1/journal", "10.1/noise"])
        self.assertEqual(result["candidate_count"], 201)
        self.assertEqual(mock_search.call_count, 2)

    @patch("app.http_client.request")
    def test_crossref_precise_fallback_verifies_titles(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {"message": {
            "total-results": 500, "items": [
                {"DOI": "10.1/match", "title": ["Quantum computing with ions"]},
                {"DOI": "10.1/noise", "title": ["Chemistry using quantum methods"]},
            ]}}
        result = live_search._search_crossref(
            '"quantum computing"', mode="precise", page_size=10)
        self.assertTrue(result["limited"])
        self.assertEqual(result["total"], 1)
        self.assertEqual([p["doi"] for p in result["papers"]], ["10.1/match"])

    @patch("app.http_client.request")
    def test_crossref_broad_fallback_uses_subject_not_boolean_syntax(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {"message": {
            "total-results": 0, "items": []}}
        live_search._search_crossref(live_search._search_terms("固态电池"))
        self.assertEqual(mock_req.call_args.kwargs["params"]["query"],
                         "solid-state battery")

    @patch("app.http_client.request")
    def test_crossref_rejects_unrelated_solid_waste_electrodes(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {"message": {
            "total-results": 3068330, "items": [
                {"DOI": "10.1/cement", "title": [
                    "Mechanical performance of solid-waste-based cementitious structural electrodes"]},
                {"DOI": "10.1/battery", "title": [
                    "Interfaces in solid-state batteries"]},
            ]}}
        result = live_search._search_crossref(
            live_search._search_terms("固态电池"), page_size=100)
        self.assertEqual([p["doi"] for p in result["papers"]], ["10.1/battery"])
        self.assertEqual(result["total"], 1)
        self.assertTrue(result["limited"])

    @patch("app.http_client.request")
    def test_precise_search_accepts_detailed_query_without_title_filter(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {"meta": {"count": 0}, "results": []}
        result = live_search.query_global("solid state battery sulfide interface", mode="precise")
        params = mock_req.call_args.kwargs["params"]
        self.assertEqual(params["search"], "solid state battery sulfide interface")
        self.assertNotIn("search.exact", params)
        self.assertNotIn("title.search", params["filter"])
        self.assertEqual(result["mode"], "precise")
        self.assertGreater(live_search._topic_strength(
            "solid state battery sulfide interface",
            "solid state battery sulfide interface", {
                "title": "Sulfide interface for solid-state batteries", "abstract": ""
            }, "precise"), 0)
        self.assertEqual(live_search._topic_strength(
            "solid state battery sulfide interface",
            "solid state battery sulfide interface", {
                "title": "Solid-state battery cathodes", "abstract": ""
            }, "precise"), 0)

    @patch("app.http_client.request")
    def test_classics_require_age_and_citations(self, mock_req):
        cutoff_year = live_search.date.today().year - 5
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {
            "meta": {"count": 4}, "results": [
                {"doi": "https://doi.org/10.1/old", "title": "Solid-state battery history",
                 "publication_date": f"{cutoff_year - 1}-01-01", "cited_by_count": 200},
                {"doi": "https://doi.org/10.1/irrelevant", "title": "Lithium ion battery history",
                 "publication_date": f"{cutoff_year - 1}-01-01", "cited_by_count": 2000},
                {"doi": "https://doi.org/10.1/new", "title": "Solid-state battery update",
                 "publication_date": f"{cutoff_year + 1}-01-01", "cited_by_count": 900},
                {"doi": "https://doi.org/10.1/uncited", "title": "Solid-state battery note",
                 "publication_date": f"{cutoff_year - 1}-01-01", "cited_by_count": 0},
            ]}
        result = live_search.query_classics("solid state battery", mode="precise")
        params = mock_req.call_args.kwargs["params"]
        self.assertEqual(params["search"], "solid state battery")
        self.assertEqual(params["sort"], "cited_by_count:desc")
        self.assertIn("to_publication_date:" + result["cutoff"], params["filter"])
        self.assertEqual([p["doi"] for p in result["papers"]], ["10.1/old"])

    @patch("app.http_client.request")
    def test_wikidata_translates_an_exact_chinese_concept(self, mock_req):
        live_search._search_terms.cache_clear()
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {"search": [{
            "label": "quantum computing", "description": "research field",
            "match": {"text": "量子计算", "language": "zh"},
        }]}
        self.assertEqual(live_search._search_terms("量子计算"), '"quantum computing"')
        self.assertEqual(mock_req.call_args.args[0], live_search.WIKIDATA_API)
        live_search._search_terms.cache_clear()

    @patch("app.http_client.request")
    def test_openalex_parsing(self, mock_req):
        # Mock OpenAlex response
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "meta": {"count": 1},
            "results": [{
                "doi": "https://doi.org/10.1038/s41586-020-2649-2",
                "title": "Language Models are Few-Shot Learners",
                "publication_date": "2020-05-28",
                "cited_by_count": 25000,
                "primary_location": {
                    "source": {"display_name": "arXiv", "issn_l": None, "host_organization_name": "Cornell"}
                },
                "authorships": [
                    {"author": {"display_name": "Tom B. Brown"}},
                    {"author": {"display_name": "Benjamin Mann"}}
                ],
                "abstract_inverted_index": {"Recent": [0], "work": [1], "demonstrates": [2]},
                "open_access": {"is_oa": True, "oa_url": "https://arxiv.org/pdf/2005.14165"},
                "primary_topic": {"display_name": "Natural Language Processing"}
            }]
        }
        mock_req.return_value = mock_resp

        res = live_search.query_global("few-shot learners")
        self.assertEqual(res["source"], "openalex")
        self.assertEqual(len(res["papers"]), 1)
        p = res["papers"][0]
        self.assertEqual(p["doi"], "10.1038/s41586-020-2649-2")
        self.assertIn("Language Models", p["title"])
        self.assertEqual(p["cited_by"], 25000)
        self.assertTrue(p["is_oa"])
        self.assertEqual(p["oa_url"], "https://arxiv.org/pdf/2005.14165")
        self.assertEqual(p["authors"], "Tom B. Brown, Benjamin Mann")
        self.assertEqual(p["journal_tier"], 0)
        self.assertEqual(p["abstract"], "Recent work demonstrates")
        self.assertEqual(res["pages"], 1)
        filt = mock_req.call_args.kwargs["params"]["filter"]
        self.assertIn("to_publication_date:", filt)

    @patch("app.http_client.request")
    def test_future_dated_work_is_not_shown(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {
            "meta": {"count": 1}, "results": [{
                "doi": "https://doi.org/10.1/future", "title": "Future paper",
                "publication_date": "2045-12-10",
            }]}
        res = live_search.query_global("future topic", sort="date")
        self.assertEqual(res["source"], "openalex")
        self.assertEqual(res["papers"], [])
        self.assertEqual(mock_req.call_count, 1)
        self.assertEqual(mock_req.call_args.kwargs["params"]["sort"],
                         "publication_date:desc,relevance_score:desc")

    @patch("app.http_client.request")
    def test_preprint_without_doi_keeps_its_openalex_link(self, mock_req):
        mock_req.return_value = MagicMock(ok=True)
        mock_req.return_value.json.return_value = {
            "meta": {"count": 1}, "results": [{
                "id": "https://openalex.org/W123456", "title": "A new learning algorithm",
                "publication_date": "2026-09-20", "type": "preprint",
                "primary_location": {"landing_page_url": "https://arxiv.org/abs/2609.12345"},
            }]}
        paper = live_search.query_global("learning algorithm")["papers"][0]
        self.assertEqual(paper["doi"], "openalex:w123456")
        self.assertEqual(paper["url"], "https://arxiv.org/abs/2609.12345")
        self.assertIn("conference-paper", mock_req.call_args.kwargs["params"]["filter"])

    @patch("app.http_client.request")
    def test_crossref_fallback(self, mock_req):
        # OpenAlex fails, Crossref succeeds
        openalex_resp = MagicMock()
        openalex_resp.ok = False
        openalex_resp.status = 500
        openalex_resp.error = "internal error"

        crossref_resp = MagicMock()
        crossref_resp.ok = True
        crossref_resp.json.return_value = {
            "message": {
                "total-results": 1,
                "items": [{
                    "DOI": "10.1145/3065386",
                    "title": ["ImageNet Classification with Deep CNNs"],
                    "container-title": ["Communications of the ACM"],
                    "author": [{"given": "Alex", "family": "Krizhevsky"}],
                    "published": {"date-parts": [[2017, 5, 23]]},
                    "is-referenced-by-count": 110000
                }]
            }
        }
        mock_req.side_effect = [openalex_resp, crossref_resp]

        res = live_search.query_global("imagenet classification")
        self.assertEqual(res["source"], "crossref")
        self.assertEqual(len(res["papers"]), 1)
        p = res["papers"][0]
        self.assertEqual(p["doi"], "10.1145/3065386")
        self.assertIn("ImageNet Classification", p["title"])
        self.assertEqual(p["cited_by"], 110000)

    @patch("app.http_client.request")
    def test_both_sources_unavailable_is_not_reported_as_no_papers(self, mock_req):
        mock_req.return_value = MagicMock(ok=False, status=503, error="unavailable")
        res = live_search.query_global("quantum computing", sort="date")
        self.assertEqual(mock_req.call_count, 2)
        self.assertTrue(res["unavailable"])
        self.assertEqual(res["source"], "unavailable")
        self.assertEqual(res["papers"], [])

    @patch("app.http_client.request")
    def test_malformed_primary_response_uses_crossref(self, mock_req):
        malformed = MagicMock(ok=True)
        malformed.json.return_value = {"unexpected": "shape"}
        backup = MagicMock(ok=True)
        backup.json.return_value = {"message": {"items": [], "total-results": 0}}
        mock_req.side_effect = [malformed, backup]
        res = live_search.query_global("microbiome")
        self.assertEqual(res["source"], "crossref")
        self.assertEqual(res["total"], 0)
        self.assertFalse(res.get("unavailable", False))


if __name__ == "__main__":
    unittest.main()
