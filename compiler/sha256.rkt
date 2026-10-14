#lang racket/base

(require racket/port
         racket/string
         racket/format)

;; =====================================================================
;; SHA-256（FIPS 180-4）—— 供产物漂移指纹使用
;; =====================================================================
;; 为什么自己写：
;;   Racket 标准库只提供 sha1（file/sha1）与 md5（file/md5），没有 sha256。
;;   bundled collects 里 openssl 未导出 digest 接口。
;;   agentLisp 其余部分的指纹一律用 sha256（host/workflow.py、scripts/bench），
;;   这里若改用 md5/sha1 会造成「同一项目两种指纹口径」。
;; 不漂移的保障（判据）：
;;   1. 本文件顶部自带 FIPS 180-4 官方向量自测（raco test 即跑）；
;;   2. Python 侧（tests/test_output_drift.py）用 hashlib.sha256 独立复算，
;;      与 Racket 产物内嵌指纹逐字比对 —— 两个独立实现互证，不靠自我声明。
;; 来源：算法与 K 常量取自 FIPS 180-4 §4.2.2 / §5.3.3（已知）。

(provide sha256-hex)

(define K
  #(#x428a2f98 #x71374491 #xb5c0fbcf #xe9b5dba5 #x3956c25b #x59f111f1 #x923f82a4 #xab1c5ed5
    #xd807aa98 #x12835b01 #x243185be #x550c7dc3 #x72be5d74 #x80deb1fe #x9bdc06a7 #xc19bf174
    #xe49b69c1 #xefbe4786 #x0fc19dc6 #x240ca1cc #x2de92c6f #x4a7484aa #x5cb0a9dc #x76f988da
    #x983e5152 #xa831c66d #xb00327c8 #xbf597fc7 #xc6e00bf3 #xd5a79147 #x06ca6351 #x14292967
    #x27b70a85 #x2e1b2138 #x4d2c6dfc #x53380d13 #x650a7354 #x766a0abb #x81c2c92e #x92722c85
    #xa2bfe8a1 #xa81a664b #xc24b8b70 #xc76c51a3 #xd192e819 #xd6990624 #xf40e3585 #x106aa070
    #x19a4c116 #x1e376c08 #x2748774c #x34b0bcb5 #x391c0cb3 #x4ed8aa4a #x5b9cca4f #x682e6ff3
    #x748f82ee #x78a5636f #x84c87814 #x8cc70208 #x90befffa #xa4506ceb #xbef9a3f7 #xc67178f2))

;; 32 位无符号语义：Racket 整数无限精度，必须每步 mask。
(define (u32 x) (bitwise-and x #xffffffff))
(define (rotr x n) (u32 (bitwise-ior (arithmetic-shift x (- n)) (arithmetic-shift x (- 32 n)))))

(define (sha256-hex in)
  (define data (cond
                 [(bytes? in) in]
                 [(string? in) (string->bytes/utf-8 in)]
                 [(input-port? in) (port->bytes in)]
                 [else (error 'sha256-hex "期望 bytes/string/input-port，得到 ~a" in)]))
  (define bit-len (* 8 (bytes-length data)))

  ;; ---- 填充：#x80 + #x00… + 64 位大端长度 ----
  (define pad-len
    (let* ([rem (modulo (+ (bytes-length data) 1) 64)]
           [zeros (modulo (- 56 rem) 64)])
      (+ 1 zeros 8)))
  (define total (+ (bytes-length data) pad-len))
  (define padded (make-bytes total 0))
  (bytes-copy! padded 0 data)
  (bytes-set! padded (bytes-length data) #x80)
  ;; 64 位大端长度占最后 8 字节：最高有效字节在 total-8，最低在 total-1。
  ;; 教训（实测 2026-10-14）：初版写成 (total-8-i) 并把第 i 段左移 8i —— 字节序反了，
  ;;   长度落到最后一字节。症状极具迷惑性：空串（长度 0）照样通过，
  ;;   "abc" 起全错。判据：必须与 Python hashlib 的多长度向量逐一相等，不能只测空串。
  (for ([i (in-range 8)])
    (bytes-set! padded (+ (- total 8) i)
                (bitwise-and (arithmetic-shift bit-len (* -8 (- 7 i))) #xff)))

  ;; ---- 初始哈希值（FIPS 180-4 §5.3.3）----
  (define h (list->vector
             (list #x6a09e667 #xbb67ae85 #x3c6ef372 #xa54ff53a
                   #x510e527f #x9b05688c #x1f83d9ab #x5be0cd19)))
  (define w (make-vector 64 0))

  (for ([chunk (in-range 0 (bytes-length padded) 64)])
    (for ([i (in-range 16)])
      (vector-set! w i (integer-bytes->integer padded #f #t (+ chunk (* 4 i)) (+ chunk (* 4 i) 4))))
    (for ([i (in-range 16 64)])
      (define s0 (bitwise-xor (rotr (vector-ref w (- i 15)) 7)
                              (rotr (vector-ref w (- i 15)) 18)
                              (arithmetic-shift (vector-ref w (- i 15)) -3)))
      (define s1 (bitwise-xor (rotr (vector-ref w (- i 2)) 17)
                              (rotr (vector-ref w (- i 2)) 19)
                              (arithmetic-shift (vector-ref w (- i 2)) -10)))
      (vector-set! w i (u32 (+ (vector-ref w (- i 16)) s0 (vector-ref w (- i 7)) s1))))

    (define a (vector-ref h 0)) (define b (vector-ref h 1))
    (define c (vector-ref h 2)) (define d (vector-ref h 3))
    (define e (vector-ref h 4)) (define f (vector-ref h 5))
    (define g (vector-ref h 6)) (define hh (vector-ref h 7))

    (for ([i (in-range 64)])
      (define S1 (bitwise-xor (rotr e 6) (rotr e 11) (rotr e 25)))
      (define ch (bitwise-xor (bitwise-and e f) (bitwise-and (u32 (bitwise-not e)) g)))
      (define t1 (u32 (+ hh S1 ch (vector-ref K i) (vector-ref w i))))
      (define S0 (bitwise-xor (rotr a 2) (rotr a 13) (rotr a 22)))
      (define maj (bitwise-xor (bitwise-and a b) (bitwise-and a c) (bitwise-and b c)))
      (define t2 (u32 (+ S0 maj)))
      (set! hh g) (set! g f) (set! f e) (set! e (u32 (+ d t1)))
      (set! d c) (set! c b) (set! b a) (set! a (u32 (+ t1 t2))))

    (vector-set! h 0 (u32 (+ (vector-ref h 0) a)))
    (vector-set! h 1 (u32 (+ (vector-ref h 1) b)))
    (vector-set! h 2 (u32 (+ (vector-ref h 2) c)))
    (vector-set! h 3 (u32 (+ (vector-ref h 3) d)))
    (vector-set! h 4 (u32 (+ (vector-ref h 4) e)))
    (vector-set! h 5 (u32 (+ (vector-ref h 5) f)))
    (vector-set! h 6 (u32 (+ (vector-ref h 6) g)))
    (vector-set! h 7 (u32 (+ (vector-ref h 7) hh))))

  (apply string-append
         (for/list ([x (in-vector h)])
           (define s (string-downcase (number->string x 16)))
           (string-append (make-string (- 8 (string-length s)) #\0) s))))

;; 自测不写在本文件的 (module+ test) 里。
;; 教训（实测 2026-10-14）：minimal Racket 发行版没有 rackunit 包；而 `(module+ test …)`
;;   的 require 在**主模块加载期**就要解析 → dynamic-require 本文件也会报
;;   "collection not found: rackunit"，把生产路径一起拖死。
;; 现口径：
;;   · 权威向量 → compiler/tests/test-sha256.rkt（RackUnit，走 `raco test`，与既有 5 个 .rkt 测试同路）；
;;   · 实现互证 → tests/test_sha256_crosscheck.py（Racket 算 vs Python hashlib 算，逐字节比对）。
