import SwiftUI

struct ProfileView: View {

    @StateObject var viewModel = ProfileViewModel()

    var body: some View {
        VStack {
            Text(viewModel.username)

            Button("Show Profile") {
                viewModel.loadProfile()
            }
        }
    }
}