from conans import ConanFile, tools
import os

class CrashpadConan(ConanFile):
    name = "crashpad"

    # crashpad does not have tagged releases, instead we track commit ids that
    # show up in official builds of Chromium every now and then...
    commit_id = "ee1d5124a2bfec578a1474b048cf934d92dcf7ba"
    version = commit_id[:7]

    license = "Apache License 2.0"
    url = "https://chromium.googlesource.com/crashpad/crashpad"
    description = "Crashpad is a crash-reporting system."
    settings = "os", "compiler", "build_type", "arch"
    exports = "patches/*"
    short_paths = True

    _scratch_dir = "srcbuild-%s" % version
    _source_dir = os.path.join(_scratch_dir, "crashpad")
    _build_name = "out/Conan"
    _build_dir = os.path.join(_source_dir, _build_name)

    def _depot_tools(self):
        return os.path.join(self.source_folder, "depot_tools")

    def _crashpad_source_base(self):
        return os.path.join(self.source_folder, "crashpad_source")

    def _crashpad_source(self):
        return os.path.join(self._crashpad_source_base(), "crashpad")

    def build_requirements(self):
        self.build_requires("depot_tools_installer/master@nexenio/testing")
        self.build_requires("ninja_installer/1.9.0@bincrafters/stable")

    def source(self):
        tools.mkdir(self._scratch_dir)
        with tools.chdir(self._scratch_dir):
            self.run("fetch crashpad")
        tools.patch(base_path=os.path.join(self._source_dir, "third_party/mini_chromium/mini_chromium"),
                    patch_file="patches/dynamic_crt.patch")

    def _setup_args_gn(self):
        args = []
        if self.settings.build_type == "Debug":
            args += [ "is_debug=true" ]
        if self.settings.os == "Macos" and self.settings.get_safe("os.version"):
            args += [ "mac_deployment_target=\\\"%s\\\"" % self.settings.os.version ]
        if self.settings.os == "Windows":
            args += [ "dynamic_crt=true" ]
        return " ".join(args)

    def build(self):
        with tools.chdir(self._source_dir):
            self.run("gn gen %s --args=\"%s\"" % (self._build_name, self._setup_args_gn()))
            self.run("ninja -j%d -C %s" % (tools.cpu_count(), self._build_name))

    def _copy_lib(self, src_dir):
        self.copy("*.a", dst="lib", 
                  src=os.path.join(self._build_dir, src_dir), keep_path=False)
        self.copy("*.lib", dst="lib", 
                  src=os.path.join(self._build_dir, src_dir), keep_path=False)
        
    def _copy_headers(self, dst_dir, src_dir):
        self.copy("*.h", dst=os.path.join("include", dst_dir), 
                         src=os.path.join(self._source_dir, src_dir))

    def _copy_bin(self, src_bin):
        self.copy(src_bin, src=self._build_dir, dst="bin")
        self.copy("%s.exe" % src_bin, src=self._build_dir, dst="bin")

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_dir, 
                             ignore_case=True, keep_path=False)

        self._copy_headers("crashpad/client", "client")
        self._copy_headers("crashpad/util",   "util")
        self._copy_headers("mini_chromium",   "third_party/mini_chromium/mini_chromium")
        self._copy_lib("obj/client")
        self._copy_lib("obj/util")
        self._copy_lib("obj/third_party/mini_chromium")
        self._copy_bin("crashpad_handler")

    def package_info(self):
        self.cpp_info.includedirs = [ "include/crashpad", "include/mini_chromium" ]
        self.cpp_info.libdirs = [ "lib" ]
        self.cpp_info.libs = tools.collect_libs(self)

        if self.settings.os == "Macos":
            self.cpp_info.exelinkflags.append("-framework CoreFoundation")
            self.cpp_info.exelinkflags.append("-framework CoreGraphics")
            self.cpp_info.exelinkflags.append("-framework CoreText")
            self.cpp_info.exelinkflags.append("-framework Security")
            self.cpp_info.exelinkflags.append("-framework IOKit")
            self.cpp_info.exelinkflags.append("-lbsm")
            self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags
