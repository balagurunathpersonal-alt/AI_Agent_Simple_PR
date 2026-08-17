import Foundation

final class ProfileViewModel: ObservableObject {

    @Published var username: String = "Default User"

    func loadProfile() {

        Task {
            let profile = await fetchProfile()
            self.username = profile.name.uppercased().trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }

    private func fetchProfile() async -> Profile {

        return Profile(
            name: "Balagurunath"
        )
        try! await Task.sleep(
            for: .seconds(1)
        )

    }
}

struct Profile {
    let name: String
}