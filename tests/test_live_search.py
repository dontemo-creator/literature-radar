# -*- coding: utf-8 -*-
"""Unit tests for multi-disciplinary real-time academic search."""
from __future__ import annotations

import pathlib
import sys
import unittest
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

        res = live_search.query_global("imagenet alexnet")
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
