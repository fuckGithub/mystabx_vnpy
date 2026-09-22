import 'dart:io';

import 'package:gm_crypto/gm_crypto.dart';

void main() {
  const pub =
      '04427f6baf23b6cb98373c94de48abbef82725f2968e97c4e9253f04e9416a931e4035500c14e5f09ddfc3acdfe22a88d6e10697ff9fafb7ab8de17a1b076ccf1a';
  // 默认 cipherMode = C1C3C2（与后端 gmssl mode=1 一致）
  final enc = SM2.encrypt('Admin@12345', pub);
  stdout.writeln('encrypted: $enc');
  File('/tmp/sm2_enc_flutter.txt').writeAsStringSync(enc);
  stdout.writeln('written len: ${enc.length}');
}