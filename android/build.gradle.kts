plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
}

// Optional per-machine build output location (set in ~/.gradle/gradle.properties or
// GRADLE_USER_HOME/gradle.properties), e.g. to keep build files out of OneDrive.
providers.gradleProperty("saltmeter.buildRoot").orNull?.let { root ->
    allprojects {
        layout.buildDirectory.set(file("$root/${project.name}"))
    }
}
