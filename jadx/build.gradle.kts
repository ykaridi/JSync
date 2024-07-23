plugins {
    kotlin("jvm") version "1.9.23"
}

group = "com.ykaridi.jsync"
version = "1.0"

repositories {
    mavenCentral()
}

dependencies {
    compileOnly("io.github.skylot:jadx-core:1.5.0")

    implementation("org.python:jython-standalone:2.7.3b1")

    implementation("org.slf4j:slf4j-api:1.7.30")
    implementation("org.slf4j:slf4j-simple:1.7.30")
}

tasks {
    jar {
        archiveFileName.set("JSync.jar")
        from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
    }
}