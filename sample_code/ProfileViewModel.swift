import Foundation

final class ProfileViewModel: ObservableObject {

    @Published var username: String = ""

    func loadProfile() {

        Task {
            let profile = await fetchProfile()
            self.username = profile.name.uppercased()
        }
    }

    private func fetchProfile() async -> Profile {

        try! await Task.sleep(
            for: .seconds(1)
        )

        return Profile(
            name: "Balagurunath"
        )
    }
}

struct Profile {
    let name: String
}