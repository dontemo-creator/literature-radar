// Build-time verification only: decode QR images with Apple's Vision framework
// so the pure-Python encoder in app/qrcode.py can be proven to produce codes a
// real camera pipeline can read.
//
//   swift tools/qr_verify.swift <image.png> [more.png ...]
//
// Prints one line per file:  <path>\t<decoded payload>   (or "\t<ERROR ...>")

import Foundation
import Vision
import CoreGraphics
import ImageIO

func decode(_ path: String) -> String {
    guard let url = URL(string: "file://" + path),
          let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        return "<ERROR cannot read image>"
    }
    let request = VNDetectBarcodesRequest()
    request.symbologies = [.qr]
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    do {
        try handler.perform([request])
    } catch {
        return "<ERROR vision failed: \(error)>"
    }
    guard let results = request.results, !results.isEmpty else {
        return "<ERROR no barcode found>"
    }
    let payloads = results.compactMap { $0.payloadStringValue }
    if payloads.isEmpty { return "<ERROR barcode found but no payload>" }
    return payloads.joined(separator: "|")
}

let args = Array(CommandLine.arguments.dropFirst())
if args.isEmpty {
    print("usage: swift qr_verify.swift <image.png> ...")
    exit(2)
}
for path in args {
    let abs = path.hasPrefix("/") ? path : FileManager.default.currentDirectoryPath + "/" + path
    print("\(path)\t\(decode(abs))")
}
