import java.io.FileInputStream
import java.util.Base64
import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// 读取签名配置（key.properties 已被 .gitignore 排除，禁止硬编码凭据）
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

// -- 版本号单一来源：lib/env/.env.<ENV>（APP_VERSION=versionName / APP_BUILD=versionCode）。
//    Flutter 将 --dart-define 以 base64 编码经 -Pdart-defines 传入 Gradle，这里解码出 ENV 定位环境文件；
//    找不到环境文件时回退 pubspec（flutter.versionCode/versionName）。
val dartDefines = (project.findProperty("dart-defines") as String?) ?: ""
var buildEnv = "dev"
for (item in dartDefines.split(",")) {
    val decoded = runCatching { String(Base64.getDecoder().decode(item)) }.getOrNull()
    if (decoded != null && decoded.startsWith("ENV=")) {
        buildEnv = decoded.removePrefix("ENV=")
        break
    }
}

val envVersionProps = Properties()
val envVersionFile = rootProject.file("../lib/env/.env.$buildEnv")
if (envVersionFile.exists()) {
    envVersionFile.reader(Charsets.UTF_8).use { envVersionProps.load(it) }
}
val envVersionName = envVersionProps.getProperty("APP_VERSION")?.trim()
val envVersionCode = envVersionProps.getProperty("APP_BUILD")?.trim()?.toIntOrNull()
// 产物名前缀：优先取 .env 的 APP_NAME，缺失/为空时回退 fastapiadmin
val envAppName = envVersionProps.getProperty("APP_NAME")?.trim()?.takeIf { it.isNotEmpty() } ?: "fastapiadmin"

// 产物文件名（对齐原生 Android applicationVariants.outputs.all 控制方式）：
// 按 APP_NAME-<APP_VERSION>-<APP_BUILD> 原顺序拼接，末尾追加构建类型后缀
// → <APP_NAME>-<APP_VERSION>-<APP_BUILD>-<BUILD_TYPE>.apk
// 如 dev: FastapiAdmin-3.0.0-alpha-301-release.apk / -debug.apk；prod: FastapiAdmin-3.0.0-300-release.apk
val apkFileBaseName = "${envAppName}-${envVersionName ?: "1.0.0"}-${envVersionCode ?: 1}"

android {
    namespace = "com.fastapiadmin.fastapiadmin_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.fastapiadmin.fastapiadmin_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // 版本号由上方从 lib/env/.env.<ENV> 自动读取（找不到时回退 pubspec）
        versionCode = envVersionCode ?: flutter.versionCode
        versionName = envVersionName ?: flutter.versionName
    }

    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"] as String?
            keyPassword = keystoreProperties["keyPassword"] as String?
            storeFile = keystoreProperties["storeFile"]?.let { file(it) }
            storePassword = keystoreProperties["storePassword"] as String?
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }

    // release/debug 产物按 <base>-<buildType>.apk 重命名（镜像原生 applicationVariants.all + outputs.all 写法；
    // 同 applicationId 靠后缀区分；注：AGP Kotlin DSL 的 all/configureEach 为接收者式 lambda，this 即 variant/output）
    applicationVariants.configureEach {
        val variantBuildType = buildType.name
        outputs.all {
            (this as com.android.build.gradle.internal.api.BaseVariantOutputImpl)
                .outputFileName = "$apkFileBaseName-$variantBuildType.apk"
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
