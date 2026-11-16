import AppKit
import WebKit

final class MedoraApp: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    private let address = URL(string: "http://127.0.0.1:38180/")!
    private let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("Medora", isDirectory: true)
    private var logFile: URL { support.appendingPathComponent("startup.log") }
    private var startup: Process?
    private var quitting = false
    private var window: NSWindow!
    private var launchView: NSView!
    private var detail: NSTextField!
    private var spinner: NSProgressIndicator!
    private var actions: NSStackView!
    private lazy var web = WKWebView()

    func applicationDidFinishLaunching(_ notification: Notification) {
        configureMenus()
        configureWindow()
        web.navigationDelegate = self
        web.uiDelegate = self
        start()
        NSApp.activate(ignoringOtherApps: true)
    }

    private func configureMenus() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu(title: "Medora")
        appMenu.addItem(withTitle: "Quit Medora", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        main.addItem(appItem)

        let editItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        for (title, selector, key) in [
            ("Undo", "undo:", "z"), ("Cut", "cut:", "x"), ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a"),
        ] {
            editMenu.addItem(withTitle: title, action: NSSelectorFromString(selector), keyEquivalent: key)
        }
        editItem.submenu = editMenu
        main.addItem(editItem)
        NSApp.mainMenu = main
    }

    private func configureWindow() {
        let title = NSTextField(labelWithString: "Medora")
        title.font = .systemFont(ofSize: 32, weight: .semibold)
        detail = NSTextField(wrappingLabelWithString: "")
        detail.alignment = .center
        detail.textColor = .secondaryLabelColor
        detail.preferredMaxLayoutWidth = 420

        spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .small
        spinner.isDisplayedWhenStopped = false

        let logButton = NSButton(title: "Open Startup Log", target: self, action: #selector(showLog))
        let retryButton = NSButton(title: "Retry", target: self, action: #selector(start))
        actions = NSStackView(views: [logButton, retryButton])
        actions.spacing = 12

        let content = NSStackView(views: [title, detail, spinner, actions])
        content.orientation = .vertical
        content.alignment = .centerX
        content.spacing = 16
        content.translatesAutoresizingMaskIntoConstraints = false

        launchView = NSView()
        launchView.addSubview(content)
        NSLayoutConstraint.activate([
            content.centerXAnchor.constraint(equalTo: launchView.centerXAnchor),
            content.centerYAnchor.constraint(equalTo: launchView.centerYAnchor),
            content.widthAnchor.constraint(lessThanOrEqualTo: launchView.widthAnchor, constant: -48),
        ])

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 850),
            styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false
        )
        window.title = "Medora"
        window.minSize = NSSize(width: 700, height: 500)
        window.contentView = launchView
        window.center()
        window.setFrameAutosaveName("MedoraWindow")
        window.makeKeyAndOrderFront(nil)
    }

    @objc private func start() {
        guard startup == nil, !quitting else { return }
        window.contentView = launchView
        detail.stringValue = "Starting the local application and database…"
        actions.isHidden = true
        spinner.startAnimation(nil)

        do {
            try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
            try Data().write(to: logFile, options: .atomic)
            startup = try runStack("start") { [weak self] status in
                self?.finishedStarting(status)
            }
        } catch {
            showError(error.localizedDescription)
        }
    }

    private func runStack(_ command: String, completion: @escaping (Int32) -> Void) throws -> Process {
        let log = try FileHandle(forWritingTo: logFile)
        try log.seekToEnd()
        let process = Process()
        process.executableURL = Bundle.main.url(forResource: "stack", withExtension: "sh")!
        process.arguments = [command, support.path]
        process.standardOutput = log
        process.standardError = log
        process.terminationHandler = { finished in
            try? log.close()
            DispatchQueue.main.async { completion(finished.terminationStatus) }
        }
        try process.run()
        return process
    }

    private func finishedStarting(_ status: Int32) {
        startup = nil
        if quitting {
            stopAndQuit()
        } else if status == 0 {
            detail.stringValue = "Opening Medora…"
            web.load(URLRequest(url: address))
        } else if status == 12 {
            showError("Docker Desktop is required. Install and open it, then retry.")
        } else if status == 13 {
            showError("Docker Desktop is still starting. Open Docker Desktop to finish setup, then retry.")
        } else {
            showError("Medora couldn’t start. Open the startup log for details.")
        }
    }

    private func showError(_ message: String) {
        window.contentView = launchView
        detail.stringValue = message
        spinner.stopAnimation(nil)
        actions.isHidden = false
    }

    @objc private func showLog() {
        NSWorkspace.shared.open(logFile)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard !quitting else { return }
        spinner.stopAnimation(nil)
        window.contentView = webView
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        if !quitting { showError(error.localizedDescription) }
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        guard !quitting, frame.isMainFrame, frame.securityOrigin.host == address.host else {
            completionHandler()
            return
        }
        let dialog = NSAlert()
        dialog.messageText = message
        dialog.addButton(withTitle: "OK")
        dialog.beginSheetModal(for: window) { _ in completionHandler() }
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        guard !quitting, frame.isMainFrame, frame.securityOrigin.host == address.host else {
            completionHandler(false)
            return
        }
        let dialog = NSAlert()
        dialog.messageText = message
        dialog.addButton(withTitle: "Confirm")
        dialog.addButton(withTitle: "Cancel")
        dialog.beginSheetModal(for: window) { completionHandler($0 == .alertFirstButtonReturn) }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if quitting { return .terminateLater }
        quitting = true
        if let startup, startup.isRunning {
            startup.terminate()
        } else if startup == nil {
            stopAndQuit()
        }
        return .terminateLater
    }

    private func stopAndQuit() {
        do {
            _ = try runStack("stop") { _ in NSApp.reply(toApplicationShouldTerminate: true) }
        } catch {
            DispatchQueue.main.async { NSApp.reply(toApplicationShouldTerminate: true) }
        }
    }
}

let app = NSApplication.shared
let delegate = MedoraApp()
app.setActivationPolicy(.regular)
app.delegate = delegate
app.run()
