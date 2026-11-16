import AppKit
let labels = ["1. The first prompt", "2. A clear prompt", "3. With shot-speak"]
let panel = 320, gap = 4, h = 28
let w = panel * 3 + gap * 2
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
    hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSColor(calibratedWhite: 0.07, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: w, height: h).fill()
let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.boldSystemFont(ofSize: 15), .foregroundColor: NSColor.white]
for (i, t) in labels.enumerated() {
    let s = NSAttributedString(string: t, attributes: attrs)
    let size = s.size()
    s.draw(at: NSPoint(x: CGFloat(i * (panel + gap)) + (CGFloat(panel) - size.width) / 2, y: (CGFloat(h) - size.height) / 2))
}
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
