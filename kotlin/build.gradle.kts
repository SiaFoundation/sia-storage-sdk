plugins {
    kotlin("jvm") version "2.1.0"
    `maven-publish`
    signing
}

group = property("group") as String
version = property("version") as String

repositories {
    mavenCentral()
}

dependencies {
    implementation("net.java.dev.jna:jna:5.16.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.10.1")

    testImplementation(kotlin("test"))
}

kotlin {
    jvmToolchain(17)
}

tasks.test {
    useJUnitPlatform()
}

java {
    withSourcesJar()
    withJavadocJar()
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            artifactId = "siaindexd"
            from(components["java"])

            pom {
                name.set("siaindexd")
                description.set("Kotlin SDK for interacting with the Sia decentralized storage network")
                url.set("https://github.com/SiaFoundation/indexd-sdk")

                licenses {
                    license {
                        name.set("MIT License")
                        url.set("https://opensource.org/licenses/MIT")
                    }
                }

                developers {
                    developer {
                        name.set("The Sia Foundation")
                        organization.set("Sia Foundation")
                        organizationUrl.set("https://sia.tech")
                    }
                }

                scm {
                    connection.set("scm:git:git://github.com/SiaFoundation/indexd-sdk.git")
                    developerConnection.set("scm:git:ssh://github.com/SiaFoundation/indexd-sdk.git")
                    url.set("https://github.com/SiaFoundation/indexd-sdk")
                }
            }
        }
    }

    repositories {
        maven {
            name = "OSSRH"
            url = uri("https://s01.oss.sonatype.org/service/local/staging/deploy/maven2/")
            credentials {
                username = findProperty("ossrhUsername") as String? ?: System.getenv("OSSRH_USERNAME")
                password = findProperty("ossrhPassword") as String? ?: System.getenv("OSSRH_PASSWORD")
            }
        }
    }
}

signing {
    val signingKey: String? = System.getenv("SIGNING_KEY")
    val signingPassword: String? = System.getenv("SIGNING_PASSWORD")
    useInMemoryPgpKeys(signingKey, signingPassword)
    sign(publishing.publications["maven"])
}

tasks.withType<Sign>().configureEach {
    onlyIf { System.getenv("SIGNING_KEY") != null }
}
