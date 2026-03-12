package sia.indexd

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class SdkTest {
    @Test
    fun testGenerateRecoveryPhrase() {
        val phrase = generateRecoveryPhrase()
        assertTrue(phrase.isNotBlank(), "Recovery phrase should not be blank")
        val words = phrase.trim().split(" ")
        assertEquals(12, words.size, "Recovery phrase should have 12 words")
    }

    @Test
    fun testValidateRecoveryPhrase() {
        val phrase = generateRecoveryPhrase()
        validateRecoveryPhrase(phrase)
    }
}
