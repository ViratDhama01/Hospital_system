import AppKit

let size = NSSize(width: 1024, height: 1024)
let image = NSImage(size: size, flipped: false) { _ in
    let tile = NSBezierPath(roundedRect: NSRect(x: 88, y: 88, width: 848, height: 848), xRadius: 186, yRadius: 186)
    NSGradient(
        starting: NSColor(srgbRed: 0.27, green: 0.53, blue: 0.99, alpha: 1),
        ending: NSColor(srgbRed: 0.08, green: 0.30, blue: 0.76, alpha: 1)
    )!.draw(in: tile, angle: -45)

    let mark = NSBezierPath()
    mark.move(to: NSPoint(x: 306, y: 330))
    mark.line(to: NSPoint(x: 306, y: 695))
    mark.line(to: NSPoint(x: 512, y: 480))
    mark.line(to: NSPoint(x: 718, y: 695))
    mark.line(to: NSPoint(x: 718, y: 330))
    mark.lineWidth = 78
    mark.lineCapStyle = .round
    mark.lineJoinStyle = .round
    NSColor.white.setStroke()
    mark.stroke()
    return true
}

let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!
    .write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
