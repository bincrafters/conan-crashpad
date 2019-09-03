#include <map>
#include <string>
#include <vector>

#include "client/crashpad_client.h"
#include "client/settings.h"

bool startCrashpad(const base::FilePath &db,
                   const base::FilePath &handler) {
    std::string              url("http://localhost");
    std::map<std::string, std::string> annotations;
    std::vector<std::string>      arguments;

    crashpad::CrashpadClient client;
    return client.StartHandler(
        handler,
        db,
        db,
        url,
        annotations,
        arguments,
        true,
        false
    );
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        return 2;
    }

    base::FilePath db(argv[1]);
    base::FilePath handler(argv[2]);

    return startCrashpad(db, handler) ? 0 : 1;
}
