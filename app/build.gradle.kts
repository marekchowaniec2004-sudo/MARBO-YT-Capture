plugins {
    id("com.android.application")
}

android {
    namespace = "pl.marbo.ytcapture"
    compileSdk = 35

    defaultConfig {
        applicationId = "pl.marbo.ytcapture"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
