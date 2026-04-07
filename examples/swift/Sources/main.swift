import Foundation
import SiaStorageSDK

// MARK: - Logger Implementation

final class PrintLogger: Logger, @unchecked Sendable {
    func debug(msg: String) {
        print("DEBUG \(msg)")
    }

    func info(msg: String) {
        print("INFO \(msg)")
    }

    func warn(msg: String) {
        print("WARNING \(msg)")
    }

    func error(msg: String) {
        print("ERROR \(msg)")
    }
}

// MARK: - Main

@main
struct SiaStorageSDKExample {
    static func main() async {
        // Set up logging
        setLogger(logger: PrintLogger(), level: "debug")

        let appId = Data(repeating: 0x01, count: 32)
        let indexerUrl = ProcessInfo.processInfo.environment["SIA_INDEXER_URL"] ?? "https://app.sia.storage"

        do {
            let builder = try await Builder(indexerUrl: indexerUrl, appMeta: AppMeta(
                id: appId,
                name: "swift example",
                description: "an example app",
                serviceUrl: "https://example.com",
                logoUrl: nil,
                callbackUrl: nil
            ))
                .requestConnection()

            let responseUrl = try builder.responseUrl()
            print("Please approve connection: \(responseUrl)")

            let approvedBuilder = try await builder.waitForApproval()

            print("Enter mnemonic (or press Enter to generate new):")
            var mnemonic = readLine()?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

            if mnemonic.isEmpty {
                mnemonic = generateRecoveryPhrase()
                print("mnemonic: \(mnemonic)")
            }

            let sdk = try await approvedBuilder.register(mnemonic: mnemonic)

            // Store the app key for later use
            let appKey = sdk.appKey()
            let appKeyData = appKey.export()
            print("App registered: \(appKeyData.base64EncodedString())")

            print("Connected to indexer")

            var start = Date()
            let obj = try await sdk.upload(data: "hello from upload()!".data(using: .utf8)!)
            try await sdk.pinObject(object: obj)
            var elapsed = Date().timeIntervalSince(start)
            print("Uploaded and pinned \(obj.size()) bytes with upload() in \(String(format: "%.2f", elapsed))s")

            start = Date()
            let downloadedSimple = try await sdk.download(object: obj)
            elapsed = Date().timeIntervalSince(start)
            if let content = String(data: downloadedSimple, encoding: .utf8) {
                print("Downloaded with download(): \"\(content)\" in \(String(format: "%.2f", elapsed))s")
            }

            print("\nUpload Packing Example...")

            // Packed upload example
            start = Date()
            let upload = await sdk.uploadPacked(options: UploadOptions())

            for i in 0..<10 {
                let size = try await upload.add(data: "hello, world \(i)!".data(using: .utf8)!)
                let remaining = upload.remaining()
                print("upload \(i) added \(size) bytes (\(remaining) remaining)")
            }

            let objects = try await upload.finalize()
            elapsed = Date().timeIntervalSince(start)
            print("Upload finished \(objects.count) objects in \(String(format: "%.2f", elapsed))s")

            // Pin each object to the indexer
            for object in objects {
                try await sdk.pinObject(object: object)
                print("Pinned object \(object.id())")
            }

            // Download example
            guard let lastObject = objects.last else {
                print("No objects were uploaded")
                return
            }
            start = Date()
            print("Downloading object \(lastObject.id()) \(lastObject.size()) bytes")
            let downloadedData = try await sdk.download(object: lastObject, options: DownloadOptions())
            elapsed = Date().timeIntervalSince(start)
            print("Downloaded object \(lastObject.id()) with \(downloadedData.count) bytes in \(String(format: "%.2f", elapsed))s")

        } catch {
            print("Error: \(error)")
        }
    }
}
