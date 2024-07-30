# BUILD file

load("@rules_kotlin//kotlin:kotlin.bzl", "kt_jvm_library")

kt_jvm_library(
    name = "jsync-kt",
    srcs = glob(["src/main/kotlin/**/*.kt"]),
    deps = [
        "@maven//:io_github_skylot_jadx_core",
        "@maven//:org_python_jython_standalone"
    ],
)

java_binary(
    name = "jsync",
    main_class = "com.ykaridi.jsync.JSyncPlugin",  # Replace with your actual main class
    runtime_deps = [
        "@maven//:org_python_jython_standalone",
        ":jsync-kt"
    ],
    deploy_manifest_lines=["a"],
    use_launcher=False,
)