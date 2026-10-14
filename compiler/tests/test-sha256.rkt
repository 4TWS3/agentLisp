#lang racket/base

;; =====================================================================
;; SHA-256 权威向量测试（FIPS 180-4）
;; =====================================================================
;; 为什么要独立文件：
;;   minimal Racket 发行版没有 rackunit 包，而 `(module+ test …)` 的 require
;;   在**主模块加载期**解析 → 桩进 sha256.rkt 会让 dynamic-require 也失败。
;;   故测试独立成本文件，只在 `raco test compiler/tests/` 时加载。
;; 为什么这些向量算权威：取自 FIPS 180-4 的官方示例（含边界长度 55/56/64）。
;; 反证价值（实测 2026-10-14）：本实现初版把 64 位长度写错字节序，
;;   **空串照样通过**，而 "abc" 起全错。若只测空串就是假绿。
;;   故这里必须有多长度向量。

(require rackunit
         racket/string
         "../sha256.rkt")

(define (a* n) (make-string n #\a))

(check-equal? (sha256-hex "") "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
              "空串（长度 0 —— 单测这一条会漏掉长度字段字节序缺陷）")

(check-equal? (sha256-hex "abc") "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
              "FIPS 180-4 官方示例 1")

(check-equal? (sha256-hex "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")
              "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
              "FIPS 180-4 官方示例 2（56 字节，跨 64 字节块边界）")

;; 填充边界：55 = 一个块内还剩 1 字节放 0x80；56 = 必须多开一个块放长度。
(check-equal? (sha256-hex (a* 55)) "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318"
              "55 字节：0x80 恰好落在块内最后一字节")
(check-equal? (sha256-hex (a* 56)) "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a"
              "56 字节：需要额外一个块")
(check-equal? (sha256-hex (a* 64)) "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"
              "64 字节：整块")

;; 长消息（1,000,000 个 0 字节）—— 多块循环的既定值
(check-equal? (sha256-hex (make-bytes 1000000 0))
              "d29751f2649b32ff572b5e0a9f541ea660a50f94ff0beedfb0b692b924cc8025"
              "1e6 字节：多块压缩循环")

;; bytes 与 string 入参必须同值（指纹算的是 UTF-8 字节）
(check-equal? (sha256-hex (string->bytes/utf-8 "abc")) (sha256-hex "abc"))
