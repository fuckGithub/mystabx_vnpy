declare module 'sm-crypto' {
  const sm2: {
    doEncrypt(msg: string, publicKey: string, cipherMode?: number): string
    doDecrypt(ciphertext: string, privateKey: string): string
    generateKeyPairHex(): { privateKey: string; publicKey: string }
    sign(msg: string, privateKey: string): string
    verifySignature(msg: string, signature: string, publicKey: string): boolean
  }
  const sm3: {
    sm3(str: string): string
  }
  const sm4: {
    encrypt(plaintext: string, key: string, options?: { mode?: string; iv?: string; padding?: string }): string
    decrypt(ciphertext: string, key: string, options?: { mode?: string; iv?: string; padding?: string }): string
  }
}
