\ C subset compiler. All source parsing and target emission run in Forth.
\ Target bit addresses; int values use LSB-first fields in MSB-first bytes.
decimal
1048576 constant cc-source-max
128 constant cc-layer-max
18176 constant cc-layer-bits
2272 constant cc-layer-bytes
98304 constant cc-image-base
98304 constant cc-static-base
variable cc-static-data
131072 constant cc-data-base
262144 constant cc-code-base
163840 constant cc-constant-base
196608 constant cc-table-base
151552 constant cc-a
151584 constant cc-b
151616 constant cc-r
151648 constant cc-carry
151680 constant cc-tmp
151712 constant cc-jaddr
151744 constant cc-lret
151776 constant cc-load-status
151808 constant cc-output
151840 constant cc-call-args
152096 constant cc-saved-result
152128 constant cc-sp
152192 constant cc-stack-message
152384 constant cc-pointer-message
153024 constant cc-mul-a
153056 constant cc-mul-b
153088 constant cc-mul-result
153120 constant cc-mul-return
153216 constant cc-div-n
153248 constant cc-div-d
153280 constant cc-div-q
153312 constant cc-div-r
153344 constant cc-div-return
153376 constant cc-div-count
153408 constant cc-div-carry
153440 constant cc-div-sign-q
153472 constant cc-div-sign-r
153504 constant cc-div-signed
153536 constant cc-div-mod
153600 constant cc-shift-message
153856 constant cc-divide-message
154112 constant cc-shift-value
154144 constant cc-shift-count
154176 constant cc-shift-return
154208 constant cc-shift-right
154240 constant cc-shift-signed
155648 constant cc-function-description-base
8388608 constant cc-stack-base
16384 constant cc-frame-bits
16760832 constant cc-stack-last

\ Small local-name compiler over pForth's existing local primitives.
create cc-local-names 256 allot
variable cc-local-count
: cc-local-name ( i -- addr ) 32 * cc-local-names + ;
create cc-local-fetch-xts
' (1_LOCAL@) , ' (2_LOCAL@) , ' (3_LOCAL@) , ' (4_LOCAL@) ,
' (5_LOCAL@) , ' (6_LOCAL@) , ' (7_LOCAL@) , ' (8_LOCAL@) ,
: cc-local-hook ( word -- flag )
  dup count s" ;" compare 0= if
    drop compile (local.exit) 0 local-compiler ! 0 exit
  then
  dup count s" exit" compare 0= if
    drop compile (local.exit) compile exit -1 exit
  then
  cc-local-count @ 0 do
    dup count i cc-local-name count compare 0= if
      drop i cells cc-local-fetch-xts + @ compile, -1 unloop exit
    then
  loop drop 0 ;
: L{ ( compilation: names } -- )
  0 cc-local-count !
  begin bl lword dup count s" }" compare while
    dup c@ 31 > cc-local-count @ 8 >= or if -1 throw then
    count cc-local-count @ cc-local-name place 1 cc-local-count +!
  repeat drop
  cc-local-count @ [compile] literal compile (local.entry)
  ['] cc-local-hook local-compiler ! ; immediate

create cc-source cc-source-max 1+ allot
variable cc-length
variable cc-pos
variable cc-token
variable cc-token-start
variable cc-token-size
variable cc-number
variable cc-number-type
variable cc-unevaluated
: cc-fail ( addr len -- )
  ." copy-c error at byte " cc-token-start @ . type cr 2 cs-exit ;
: cc-limit ( flag -- ) if s" capacity exceeded" cc-fail then ;

create cc-image 20480 cc-layer-max cc-layer-bytes * + allot
cc-image 20480 cc-layer-max cc-layer-bytes * + 0 fill
create cc-record 37 allot
create cc-reversed 256 allot
: cc-prepare-reverse
  256 0 do 0 i 8 0 do swap 2 * over 1 and + swap 1 rshift loop
    drop cc-reversed i + c! loop ;
cc-prepare-reverse

: cc-bits! ( value width position buffer -- ) cc-reversed cs-put-bits ;
: cc-value! ( value bits target -- ) cc-image-base - cc-image cc-bits! ;

variable cc-row-n
variable cc-row-d
variable cc-row-s
variable cc-row-bit
variable cc-row-buffer
: cc-row-at ( n dst src bit buffer -- )
  cc-row-buffer ! cc-row-bit ! cc-row-s ! cc-row-d ! cc-row-n !
  cc-row-n @ 23 cc-row-bit @ cc-row-buffer @ cc-bits!
  cc-row-d @ 24 cc-row-bit @ 23 + cc-row-buffer @ cc-bits!
  cc-row-s @ 24 cc-row-bit @ 47 + cc-row-buffer @ cc-bits! ;
variable cc-emission-base
variable cc-emission-buffer
: cc-row ( n dst src target-bit -- )
  cc-unevaluated @ if 2drop 2drop exit then
  cc-emission-base @ - cc-emission-buffer @ cc-row-at ;

variable cc-layer
variable cc-slot
variable cc-constants
variable cc-data
variable cc-infer-depth
variable cc-infer-target
variable cc-infer-length
variable cc-origin
create cc-fold-flags 2048 allot
create cc-fold-values 2048 cells allot
create cc-pointer-origins 2048 cells allot
create cc-literal-values 512 cells allot
: cc-current ( -- target ) cc-layer @ cc-layer-bits * cc-origin @ + ;
: cc-new 1 cc-layer +! cc-layer @ cc-layer-max >= cc-limit 3 cc-slot ! ;
: cc-end ( target -- )
  cc-layer-bits 0 rot cc-current 255 71 * + cc-row ;
: cc-jump ( target -- ) cc-unevaluated @ if drop exit then cc-end cc-new ;
: cc-room ( count -- ) cc-slot @ + 255 > if
    cc-current cc-layer-bits + cc-jump then ;
: cc-raw-op ( n dst src -- )
  1 cc-room cc-current cc-slot @ 71 * + cc-row 1 cc-slot +! ;
: cc-frame? ( address -- flag )
  dup cc-data-base >= swap cc-data-base cc-frame-bits + < and ;
: cc-frame-extra ( address -- count ) cc-frame? if 1 else 0 then ;
: cc-frame-address ( address -- address )
  dup cc-frame? if cc-data-base - cc-stack-base + then ;
: cc-op ( n dst src -- ) 0 L{ n dst src target }
  cc-unevaluated @ if exit then
  1 dst cc-frame-extra + src cc-frame-extra + cc-room
  cc-slot @ dst cc-frame-extra + src cc-frame-extra + 4 (local!)
  dst cc-frame? if 10 target 71 * 37 + cc-sp 14 + cc-raw-op then
  src cc-frame? if 10 target 71 * 61 + cc-sp 14 + cc-raw-op then
  n dst cc-frame-address src cc-frame-address cc-raw-op ;
: cc-boundary ( -- target )
  cc-slot @ 3 <> if cc-current cc-layer-bits + cc-jump then cc-current ;
: cc-cell ( -- target )
  cc-data @ 31 + 31 invert and cc-data !
  cc-data @ 32 + 147456 > cc-limit
  0 cc-fold-flags cc-data @ cc-data-base - 8 / + c!
  0 cc-pointer-origins cc-data @ cc-data-base - 8 / cells + !
  cc-data @ 32 cc-data +! ;
: cc-const ( value -- target )
  cc-constants @ 32 cc-constants +!
  cc-constants @ 180224 > cc-limit >r
  dup cc-literal-values r@ cc-constant-base - 32 / cells + !
  32 r@ cc-value! r> ;
: cc-patch ( target value -- ) cc-unevaluated @ if 2drop exit then swap 32 swap cc-value! ;
: cc-dynamic ( source -- )
  1 cc-room 24 18152 rot cc-op 0 cc-jump ;

\ Patch the active instruction, then perform its LUT read in the same tick.
: cc-lut1 ( dst base a -- ) L{ dst base a }
  2 a cc-frame-extra + dst cc-frame-extra + cc-room
  1 cc-slot @ 1+ a cc-frame-extra + dst cc-frame-extra + 71 * 47 + a cc-op
  1 dst base cc-op ;
: cc-lut2 ( dst base a b -- ) 0 L{ dst base a b target }
  3 a cc-frame-extra + b cc-frame-extra + dst cc-frame-extra + cc-room
  cc-slot @ 2 + a cc-frame-extra + b cc-frame-extra + dst cc-frame-extra + 5 (local!)
  1 target 71 * 47 + a cc-op
  1 target 71 * 48 + b cc-op 1 dst base cc-op ;
: cc-lut3 ( width dst base a b c stride -- ) 0 L{ width dst base a b c stride target }
  4 a cc-frame-extra + b cc-frame-extra + c cc-frame-extra + dst cc-frame-extra + cc-room
  cc-slot @ 3 + a cc-frame-extra + b cc-frame-extra + c cc-frame-extra + dst cc-frame-extra + 8 (local!)
  1 target 71 * 47 + stride + a cc-op
  1 target 71 * 48 + stride + b cc-op
  1 target 71 * 49 + stride + c cc-op
  width dst base cc-op ;
: cc-branch ( condition -- table ) L{ condition }
  cc-constants @ 63 + 63 invert and cc-constants !
  0 cc-const >r 0 cc-const drop
  3 condition cc-frame-extra + cc-room
  1 cc-slot @ 1+ condition cc-frame-extra + 71 * 52 + condition cc-op
  24 cc-jaddr r@ cc-op cc-jaddr cc-dynamic r> ;

variable cc-zero
variable cc-one
variable cc-add-entry
variable cc-sub-entry
variable cc-eq-entry
variable cc-lt-entry
variable cc-ult-entry
variable cc-and-entry
variable cc-or-entry
variable cc-xor-entry
variable cc-not-entry
variable cc-shl-entry
variable cc-shr-entry
variable cc-sar-entry
variable cc-mul-entry
variable cc-div-entry
variable cc-udiv-entry
variable cc-mod-entry
variable cc-umod-entry
variable cc-div-core
variable cc-div-error-table
variable cc-shift-error-table
variable cc-shift-core
variable cc-bool-entry
variable cc-output-entry
variable cc-stack-error-entry
variable cc-pointer-check-entry
variable cc-pointer-error-entry
variable cc-pointer-error-table
variable cc-library-layer
variable cc-library-constants
variable cc-library-end
: cc-full-add
  32 0 do
    2 cc-tmp cc-table-base cc-a i + cc-b i + cc-carry 1 cc-lut3
    1 cc-r i + cc-tmp cc-op 1 cc-carry cc-tmp 1+ cc-op
  loop cc-lret cc-dynamic ;
: cc-library-call ( entry -- )
  1 cc-room cc-current cc-layer-bits + cc-const
  24 cc-lret rot cc-op cc-jump ;
: cc-message! ( addr len target -- ) L{ text bytes target }
  bytes 0 ?do text i + c@ cc-reversed + c@ 8 target i 8 * + cc-value! loop
  10 cc-reversed + c@ 8 target bytes 8 * + cc-value! ;
: cc-bit-library ( table -- ) L{ table }
  32 0 do cc-r i + table cc-a i + cc-b i + cc-lut2 loop cc-lret cc-dynamic ;
: cc-shift-library
  cc-current cc-shift-core !
  24 cc-shift-return cc-lret cc-op
  32 cc-shift-value cc-a cc-op 32 cc-shift-count cc-b cc-op
  1 cc-carry cc-zero @ cc-op
  32 5 do cc-carry cc-table-base 24 + cc-carry cc-b i + cc-lut2 loop
  cc-carry cc-branch dup cc-shift-error-table ! cc-current cc-patch
  32 cc-a cc-shift-count cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch 0 0 0 L{ zero-table head direction-table skip }
  zero-table 32 + cc-current cc-patch cc-current 2 (local!)
  cc-shift-right cc-branch 3 (local!) direction-table cc-current cc-patch
  31 cc-shift-value 1+ cc-shift-value cc-op 1 cc-shift-value cc-zero @ cc-op
  cc-current 18152 + 4 (local!) 0 cc-jump
  direction-table 32 + cc-current cc-patch
  31 cc-shift-value cc-shift-value 1+ cc-op
  cc-shift-value 31 + cc-table-base 48 + cc-shift-value 31 + cc-shift-signed cc-lut2
  cc-boundary 24 skip cc-value!
  32 cc-a cc-shift-count cc-op 32 cc-b cc-one @ cc-op
  cc-sub-entry @ cc-library-call 32 cc-shift-count cc-r cc-op
  32 cc-a cc-shift-count cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch dup 32 + head cc-patch cc-current cc-patch
  zero-table cc-current cc-patch
  32 cc-r cc-shift-value cc-op 24 cc-lret cc-shift-return cc-op cc-lret cc-dynamic
  cc-current cc-shl-entry !
  1 cc-shift-right cc-zero @ cc-op 1 cc-shift-signed cc-zero @ cc-op cc-shift-core @ cc-jump
  cc-current cc-shr-entry !
  1 cc-shift-right cc-one @ cc-op 1 cc-shift-signed cc-zero @ cc-op cc-shift-core @ cc-jump
  cc-current cc-sar-entry !
  1 cc-shift-right cc-one @ cc-op 1 cc-shift-signed cc-one @ cc-op cc-shift-core @ cc-jump ;
: cc-multiply-library
  24 cc-mul-return cc-lret cc-op
  32 cc-mul-a cc-a cc-op 32 cc-mul-b cc-b cc-op
  32 cc-mul-result cc-zero @ cc-op
  cc-boundary L{ head }
  32 cc-a cc-mul-b cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch >r r@ 32 + cc-current cc-patch
  cc-mul-b cc-branch >r r@ 32 + cc-current cc-patch
  32 cc-a cc-mul-result cc-op 32 cc-b cc-mul-a cc-op
  cc-add-entry @ cc-library-call 32 cc-mul-result cc-r cc-op
  cc-boundary r> swap cc-patch
  31 cc-mul-a 1+ cc-mul-a cc-op 1 cc-mul-a cc-zero @ cc-op
  31 cc-mul-b cc-mul-b 1+ cc-op 1 cc-mul-b 31 + cc-zero @ cc-op
  head cc-jump r> cc-current cc-patch
  32 cc-r cc-mul-result cc-op 24 cc-lret cc-mul-return cc-op cc-lret cc-dynamic ;
: cc-div-absolute ( value -- ) L{ value }
  value 31 + cc-branch >r r@ 32 + cc-current cc-patch
  32 cc-a cc-zero @ cc-op 32 cc-b value cc-op
  cc-sub-entry @ cc-library-call 32 value cc-r cc-op
  cc-boundary r> swap cc-patch ;
: cc-division-library
  cc-current cc-div-core !
  24 cc-div-return cc-lret cc-op
  32 cc-div-n cc-a cc-op 32 cc-div-d cc-b cc-op
  32 cc-div-q cc-zero @ cc-op 32 cc-div-r cc-zero @ cc-op
  32 cc-div-count 32 cc-const cc-op
  1 cc-div-sign-q cc-zero @ cc-op 1 cc-div-sign-r cc-zero @ cc-op
  32 cc-a cc-div-d cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch dup cc-div-error-table ! 32 + cc-current cc-patch
  cc-div-signed cc-branch >r r@ 32 + cc-current cc-patch
  1 cc-div-sign-r cc-div-n 31 + cc-op
  cc-div-sign-q cc-table-base 16 + cc-div-n 31 + cc-div-d 31 + cc-lut2
  cc-div-n cc-div-absolute cc-div-d cc-div-absolute
  cc-boundary r> swap cc-patch
  cc-boundary 0 0 0 0 L{ head carry-table compare-table selection-table selection-field }
  1 cc-div-carry cc-div-r 31 + cc-op
  31 cc-div-r 1+ cc-div-r cc-op 1 cc-div-r cc-div-n 31 + cc-op
  31 cc-div-n 1+ cc-div-n cc-op 1 cc-div-n cc-zero @ cc-op
  31 cc-div-q 1+ cc-div-q cc-op 1 cc-div-q cc-zero @ cc-op
  cc-div-carry cc-branch 2 (local!) carry-table cc-current cc-patch
  32 cc-a cc-div-r cc-op 32 cc-b cc-div-d cc-op
  cc-ult-entry @ cc-library-call cc-r cc-branch 3 (local!)
  compare-table cc-current cc-patch carry-table 32 + cc-current cc-patch
  32 cc-a cc-div-r cc-op 32 cc-b cc-div-d cc-op
  cc-sub-entry @ cc-library-call 32 cc-div-r cc-r cc-op
  1 cc-div-q cc-one @ cc-op
  cc-boundary compare-table 32 + swap cc-patch
  32 cc-a cc-div-count cc-op 32 cc-b cc-one @ cc-op
  cc-sub-entry @ cc-library-call 32 cc-div-count cc-r cc-op
  32 cc-a cc-div-count cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch dup 32 + head cc-patch cc-current cc-patch
  cc-div-mod cc-branch 4 (local!) selection-table cc-current cc-patch
  32 cc-r cc-div-q cc-op 1 cc-div-carry cc-div-sign-q cc-op
  cc-current 18152 + 5 (local!) 0 cc-jump
  selection-table 32 + cc-current cc-patch
  32 cc-r cc-div-r cc-op 1 cc-div-carry cc-div-sign-r cc-op
  cc-boundary 24 selection-field cc-value!
  cc-div-carry cc-branch >r r@ 32 + cc-current cc-patch
  32 cc-b cc-r cc-op 32 cc-a cc-zero @ cc-op
  cc-sub-entry @ cc-library-call cc-boundary r> swap cc-patch
  24 cc-lret cc-div-return cc-op cc-lret cc-dynamic
  cc-current cc-udiv-entry !
  1 cc-div-signed cc-zero @ cc-op 1 cc-div-mod cc-zero @ cc-op cc-div-core @ cc-jump
  cc-current cc-div-entry !
  1 cc-div-signed cc-one @ cc-op 1 cc-div-mod cc-zero @ cc-op cc-div-core @ cc-jump
  cc-current cc-umod-entry !
  1 cc-div-signed cc-zero @ cc-op 1 cc-div-mod cc-one @ cc-op cc-div-core @ cc-jump
  cc-current cc-mod-entry !
  1 cc-div-signed cc-one @ cc-op 1 cc-div-mod cc-one @ cc-op cc-div-core @ cc-jump ;
: cc-library
  cc-code-base cc-origin ! cc-image-base cc-emission-base ! cc-image cc-emission-buffer !
  0 cc-layer ! 3 cc-slot ! cc-constant-base cc-constants !
  cc-stack-base 32 cc-sp cc-value!
  s" copy-c: stack overflow" 0 do
    dup i + c@ cc-reversed + c@ 8 cc-stack-message i 8 * + cc-value!
  loop drop
  10 cc-reversed + c@ 8 cc-stack-message 176 + cc-value!
  s" copy-c: pointer error" 0 do
    dup i + c@ cc-reversed + c@ 8 cc-pointer-message i 8 * + cc-value!
  loop drop
  10 cc-reversed + c@ 8 cc-pointer-message 168 + cc-value!
  s" copy-c: shift error" cc-shift-message cc-message!
  s" copy-c: divide by zero" cc-divide-message cc-message!
  0 cc-const cc-zero ! 1 cc-const cc-one !
  8 0 do
    i 1 and i 1 rshift 1 and + i 2 rshift 1 and +
    2 cc-table-base i 2 * + cc-value!
    i 1 and i 1 rshift 1 and = if i 2 rshift 1 and
      else i 1 rshift 1 and then
    1 cc-table-base 32 + i + cc-value!
  loop
  4 0 do
    i 1 and i 1 rshift 1 and xor
    1 cc-table-base 16 + i + cc-value!
    i 1 and i 1 rshift 1 and or
    1 cc-table-base 24 + i + cc-value!
    i 1 and i 1 rshift 1 and and
    1 cc-table-base 48 + i + cc-value!
  loop
  1 1 cc-table-base 40 + cc-value!
  cc-current cc-add-entry ! 1 cc-carry cc-zero @ cc-op cc-full-add
  cc-current cc-sub-entry !
  32 0 do cc-b i + cc-table-base 40 + cc-b i + cc-lut1 loop
  1 cc-carry cc-one @ cc-op cc-full-add
  cc-current cc-eq-entry ! 32 cc-r cc-zero @ cc-op
  1 cc-carry cc-zero @ cc-op
  32 0 do
    cc-tmp cc-table-base 16 + cc-a i + cc-b i + cc-lut2
    cc-carry cc-table-base 24 + cc-carry cc-tmp cc-lut2
  loop cc-r cc-table-base 40 + cc-carry cc-lut1 cc-lret cc-dynamic
  cc-current cc-lt-entry ! 32 cc-r cc-zero @ cc-op
  31 0 do
    1 cc-r cc-table-base 32 + cc-a i + cc-b i + cc-r 0 cc-lut3
  loop
  cc-tmp cc-table-base 40 + cc-a 31 + cc-lut1
  cc-tmp 1+ cc-table-base 40 + cc-b 31 + cc-lut1
  1 cc-r cc-table-base 32 + cc-tmp cc-tmp 1+ cc-r 0 cc-lut3
  cc-lret cc-dynamic
  cc-current cc-ult-entry ! 32 cc-r cc-zero @ cc-op
  32 0 do 1 cc-r cc-table-base 32 + cc-a i + cc-b i + cc-r 0 cc-lut3 loop
  cc-lret cc-dynamic
  cc-current cc-bool-entry ! 32 cc-r cc-zero @ cc-op
  32 0 do cc-r cc-table-base 24 + cc-r cc-a i + cc-lut2 loop
  cc-lret cc-dynamic
  cc-current cc-pointer-check-entry ! 1 cc-carry cc-zero @ cc-op
  32 21 do cc-carry cc-table-base 24 + cc-carry cc-a i + cc-lut2 loop
  cc-tmp cc-table-base 40 + cc-a 20 + cc-lut1
  cc-carry cc-table-base 24 + cc-carry cc-tmp cc-lut2
  1 cc-b cc-zero @ cc-op
  32 14 do cc-b cc-table-base 24 + cc-b cc-a i + cc-lut2 loop
  cc-tmp cc-table-base 48 + cc-a 12 + cc-a 13 + cc-lut2
  cc-tmp cc-table-base 40 + cc-tmp cc-lut1
  cc-b cc-table-base 24 + cc-b cc-tmp cc-lut2
  cc-carry cc-table-base 48 + cc-carry cc-b cc-lut2
  cc-carry cc-branch dup cc-pointer-error-table ! cc-current cc-patch
  cc-lret cc-dynamic
  cc-current cc-and-entry ! cc-table-base 48 + cc-bit-library
  cc-current cc-or-entry ! cc-table-base 24 + cc-bit-library
  cc-current cc-xor-entry ! cc-table-base 16 + cc-bit-library
  cc-current cc-not-entry !
  32 0 do cc-r i + cc-table-base 40 + cc-a i + cc-lut1 loop cc-lret cc-dynamic
  cc-shift-library
  cc-current cc-mul-entry ! cc-multiply-library
  cc-division-library
  cc-current cc-output-entry !
  32 0 do 1 cc-output i 8 / 8 * 7 + i 7 and - +
    cc-r i + cc-op loop
  cc-current cc-layer-bits + cc-jump
  32 cc-output 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-current cc-stack-error-entry !
  184 cc-stack-message 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-pointer-error-table @ 32 + cc-current cc-patch
  cc-current cc-pointer-error-entry !
  176 cc-pointer-message 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-shift-error-table @ 32 + cc-current cc-patch
  160 cc-shift-message 0 cc-current 142 + cc-row 65536 cc-jump
  cc-div-error-table @ cc-current cc-patch
  184 cc-divide-message 0 cc-current 142 + cc-row 65536 cc-jump
  cc-layer @ cc-library-layer ! cc-constants @ cc-library-constants !
  cc-current cc-library-end ! ;
cc-library

\ This small guard is installed before the large payload is read. Its code
\ is constant; only the expected count and success entry depend on the C.
4128768 constant cc-guard-data
4194304 constant cc-guard-code
create cc-guard-image cc-layer-bytes 2 * allot
create cc-guard-constants 36 allot
create cc-prelude 16384 allot
create cc-chunk 6 allot
variable cc-prelude-bytes
variable cc-preparing
: cc-three ( address -- value )
  dup c@ cc-reversed + c@ over 1+ c@ cc-reversed + c@ 8 lshift or
  swap 2 + c@ cc-reversed + c@ 16 lshift or ;
: cc-install ( target source bytes -- ) L{ target source bytes }
  bytes 0 ?do
    cc-chunk 6 0 fill source i + cc-chunk bytes i - 6 min cmove
    0 6 0 do cc-chunk i + c@ or loop
    if
      cc-record 37 0 fill
      48 target i 8 * + 18270 0 cc-record cc-row-at
      0 cc-chunk cc-three cc-chunk 3 + cc-three 71 cc-record cc-row-at
      284 0 18688 213 cc-record cc-row-at
      cc-preparing @ if
        cc-prelude-bytes @ 37 + 16384 > cc-limit
        cc-record cc-prelude cc-prelude-bytes @ + 37 cmove
        37 cc-prelude-bytes +!
      else cc-record 37 cs-write 37 <> if 1 cs-exit then then
    then
  6 +loop ;
: cc-prepare-guard
  cc-guard-image cc-layer-bytes 2 * 0 fill cc-guard-constants 36 0 fill
  4 0 do
    i 1 and i 1 rshift 1 and xor 1 32 i + cc-guard-constants cc-bits!
    i 1 and i 1 rshift 1 and or 1 40 i + cc-guard-constants cc-bits!
  loop
  cc-guard-code cc-layer-bits + 32 96 cc-guard-constants cc-bits!
  s" copy-c: load error" cc-guard-constants 16 + swap cmove
  10 cc-guard-constants 34 + c!
  cc-guard-code cc-origin ! cc-guard-code cc-emission-base !
  cc-guard-image cc-emission-buffer ! 0 cc-layer ! 4 cc-slot !
  1 cc-carry 65536 cc-op
  24 0 do
    cc-tmp cc-guard-data 32 + cc-load-status i + cc-guard-data i + cc-lut2
    cc-carry cc-guard-data 40 + cc-carry cc-tmp cc-lut2
  loop
  1 cc-slot @ 1+ 71 * 52 + cc-carry cc-op
  24 cc-jaddr cc-guard-data 64 + cc-op cc-jaddr cc-dynamic
  152 cc-guard-data 128 + 0 cc-current 142 + cc-row
  65536 cc-end
  -1 cc-preparing ! 0 cc-prelude-bytes !
  cc-guard-code cc-guard-image cc-layer-bytes 2 * cc-install
  0 cc-preparing !
  cc-code-base cc-origin ! cc-image-base cc-emission-base ! cc-image cc-emission-buffer !
  cc-library-layer @ cc-layer ! 3 cc-slot ! ;
cc-prepare-guard

: cc-raw-value ;
defer cc-fold-invoke
: cc-no-fold ( lhs rhs entry result -- ) 2drop 2drop ;
' cc-no-fold is cc-fold-invoke
defer cc-fold-invert
: cc-no-invert-fold ( source result -- ) 2drop ;
' cc-no-invert-fold is cc-fold-invert
defer cc-materialize
' cc-raw-value is cc-materialize
: cc-invoke ( lhs rhs entry -- result ) L{ lhs rhs entry }
  lhs cc-materialize 1 (local!) rhs cc-materialize 2 (local!)
  3 lhs cc-frame-extra + rhs cc-frame-extra + cc-room
  32 cc-a lhs cc-op 32 cc-b rhs cc-op
  cc-current cc-layer-bits + cc-const 24 cc-lret rot cc-op
  entry cc-jump cc-cell dup 32 swap cc-r cc-op
  lhs rhs entry 3 pick cc-fold-invoke ;
defer cc-check-truth
: cc-truth ( value -- result ) dup cc-check-truth cc-zero @ cc-bool-entry @ cc-invoke ;
: cc-invert ( value -- result ) cc-cell L{ value result }
  32 result cc-zero @ cc-op
  result cc-table-base 40 + value cc-lut1 value result cc-fold-invert result ;
\ Lexer: names and numbers refer to source bytes, never to host parsing.
: cc-peek cc-pos @ cc-length @ < if cc-source cc-pos @ + c@ else -1 then ;
: cc-step 1 cc-pos +! ;
: cc-within ( n lo hi -- flag ) over - >r - r> u< ;
: cc-alpha ( c -- flag )
  dup 97 123 cc-within over 65 91 cc-within or swap 95 = or ;
: cc-digit ( c -- flag ) 48 58 cc-within ;
: cc-namechar dup cc-alpha swap cc-digit or ;
: cc-space dup 32 = swap 9 14 cc-within or ;
: cc-scan ( char -- )
  >r cc-source cc-pos @ + cc-length @ cc-pos @ - r> scan
  drop cc-source - cc-pos ! ;
: cc-comment
  cc-step cc-step
  begin
    42 cc-scan
    cc-peek -1 = if s" unfinished comment" cc-fail then
    cc-step cc-peek 47 = if cc-step exit then
  again ;
: cc-skip
  begin
    cc-peek cc-space if cc-step else
      cc-peek 47 = cc-pos @ 1+ cc-length @ < and if
        cc-source cc-pos @ 1+ + c@ dup 47 = if
          drop 10 cc-scan
        else 42 = if cc-comment
        else exit then then
      else exit then
    then
  again ;
: cc-text cc-source cc-token-start @ + cc-token-size @ ;
: cc-is ( addr len -- flag ) cc-text compare 0= ;
: cc-hex-digit ( c -- digit )
  dup cc-digit if 48 - exit then
  dup 97 103 cc-within if 87 - exit then
  dup 65 71 cc-within if 55 - exit then drop -1 ;
: cc-literal-byte ( -- byte or -1 for splice ) 0 0 0 L{ byte value digits }
  cc-peek 1 (local!) byte -1 = if s" unfinished literal" cc-fail then
  byte 0= byte 10 = or byte 13 = or if s" invalid literal byte" cc-fail then
  cc-step byte 92 <> if byte exit then
  cc-peek 1 (local!) byte -1 = if s" unfinished literal escape" cc-fail then
  byte 0= if s" NUL in literal escape" cc-fail then
  byte 10 = if cc-step -1 exit then
  byte 13 = if cc-step cc-peek 10 = if cc-step then -1 exit then
  byte 48 56 cc-within if
    begin cc-peek 48 56 cc-within digits 3 < and while
      value 8 * cc-peek 48 - + 2 (local!) digits 1+ 3 (local!) cc-step
    repeat value 255 and exit then
  byte 120 = if cc-step
    begin cc-peek cc-hex-digit dup 0< 0= while
      value 16 * + 255 and 2 (local!) digits 1+ 3 (local!) cc-step
    repeat drop digits 0= if s" empty hex escape" cc-fail then value exit then
  byte 117 = byte 85 = or if s" universal character escape pending" cc-fail then
  cc-step
  byte 97 = if 7 exit then byte 98 = if 8 exit then
  byte 102 = if 12 exit then byte 110 = if 10 exit then
  byte 114 = if 13 exit then byte 116 = if 9 exit then
  byte 118 = if 11 exit then byte 101 = byte 69 = or if 27 exit then byte ;
: cc-character-next ( -- ) 0 0 0 L{ value bytes byte }
  cc-step begin cc-peek 39 <> while
    cc-literal-byte 3 (local!) byte 0< 0= if
      value 8 lshift byte or 1 (local!) bytes 1+ 2 (local!) then
  repeat cc-step bytes 0= if s" empty character literal" cc-fail then
  bytes 1 = value 127 > and if value 256 - 1 (local!) then
  value cc-number ! 0 cc-number-type ! 1 cc-token ! ;
variable cc-radix
variable cc-number-start
variable cc-long-suffix
variable cc-unsigned-suffix
: cc-number-next
  0 cc-long-suffix ! 0 cc-unsigned-suffix !
  0 cc-number ! 0 cc-number-type ! 10 cc-radix !
  cc-peek 48 = cc-pos @ 1+ cc-length @ < and if
    8 cc-radix ! cc-source cc-pos @ 1+ + c@
    dup 120 = over 88 = or if drop cc-step cc-step 16 cc-radix ! else
      dup 98 = swap 66 = or if cc-step cc-step 2 cc-radix ! then then
  then cc-pos @ cc-number-start !
  begin cc-peek dup cc-digit if 48 - else
    dup 97 103 cc-within if 87 - else
      dup 65 71 cc-within if 55 - else drop 99 then then then
    dup cc-radix @ <
  while
    cc-radix @ 2 = if cc-number @ 2147483647 u> else
      cc-radix @ 8 = if cc-number @ 536870911 u> else
        cc-radix @ 10 = if
          cc-number @ 429496729 u> cc-number @ 429496729 = 2 pick 5 > and or
        else cc-number @ 268435455 u> then then then
    if drop s" integer literal out of range" cc-fail then
    cc-number @ cc-radix @ * + cc-number ! cc-step
  repeat drop
  cc-pos @ cc-number-start @ = if s" malformed number" cc-fail then
  begin cc-peek dup 117 = over 85 = or over 108 = or swap 76 = or while
    cc-peek dup 117 = swap 85 = or if
      cc-unsigned-suffix @ if s" duplicate unsigned suffix" cc-fail then
      1 cc-unsigned-suffix !
    else
      cc-long-suffix @ if s" 64-bit literal unsupported" cc-fail then
      1 cc-long-suffix !
    then cc-step
  repeat
  cc-long-suffix @ if 9 else 0 then cc-unsigned-suffix @ + cc-number-type !
  cc-peek cc-namechar if s" unsupported or malformed integer suffix" cc-fail then
  cc-number @ 2147483647 u> cc-unsigned-suffix @ 0= and if
    cc-radix @ 10 = if s" 64-bit decimal literal unsupported" cc-fail then
    1 cc-number-type +!
  then
  1 cc-token ! ;
: cc-next
  cc-skip cc-pos @ cc-token-start ! 0 cc-token-size !
  cc-peek dup -1 = if drop 0 cc-token ! exit then
  dup 0= if s" NUL in source" cc-fail then
  dup 39 = if drop cc-character-next
    cc-pos @ cc-token-start @ - cc-token-size ! exit then
  dup cc-alpha if drop
    begin cc-peek cc-namechar while cc-step repeat 2 cc-token !
  else dup cc-digit if drop cc-number-next
  else cc-step cc-token !
    cc-token @ 46 = cc-peek 46 = and if
      cc-pos @ 1+ cc-length @ < if cc-source cc-pos @ 1+ + c@ 46 = if
        cc-step cc-step 267 cc-token ! then then then
    cc-token @ dup 61 = over 33 = or over 60 = or swap 62 = or
    cc-peek 61 = and if
      cc-token @ dup 61 = if drop 256 else dup 33 = if drop 257 else
        60 = if 258 else 259 then then then cc-token ! cc-step
    then
    cc-token @ dup 60 = over 62 = or over 38 = or over 124 = or
    over 43 = or swap 45 = or
    cc-peek cc-token @ = and if
      cc-token @ dup 60 = if drop 260 else dup 62 = if drop 261 else
        dup 38 = if drop 262 else dup 124 = if drop 263 else
          43 = if 264 else 265 then then then then then cc-token ! cc-step
    then
    cc-token @ dup 43 = over 45 = or over 42 = or over 47 = or
    over 37 = or over 38 = or over 94 = or over 124 = or
    over 260 = or swap 261 = or cc-peek 61 = and if
      512 cc-token +! cc-step then
    cc-token @ 45 = cc-peek 62 = and if 266 cc-token ! cc-step then
  then then cc-pos @ cc-token-start @ - cc-token-size ! ;
: cc-expect ( token -- ) cc-token @ <> if s" unexpected token" cc-fail then cc-next ;

create cc-function-names 16 32 * allot
create cc-function-linkage 16 allot
create cc-function-entry 16 cells allot
create cc-function-return 16 cells allot
create cc-function-value 16 cells allot
create cc-function-argc 16 cells allot
create cc-function-params 16 8 * cells allot
create cc-function-signatures 16 cells allot
variable cc-function-prototyped
create cc-symbol-names 128 32 * allot
create cc-symbol-address 128 cells allot
create cc-symbol-levels 128 cells allot
create cc-call-functions 128 cells allot
create cc-call-fields 128 cells allot
variable cc-call-count
variable cc-new-function
variable cc-parameter-count
variable cc-parameter-after
create cc-types 2048 allot
create cc-lvalues 2048 allot
create cc-lvalue-pointers 2048 cells allot
create cc-constant-types 512 allot
create cc-static-types 4096 allot
cc-constant-types 512 0 fill
variable cc-declared-type
variable cc-base-type
variable cc-function-type
variable cc-function-count
variable cc-function-index
variable cc-symbol-count
variable cc-main-index
variable cc-depth
variable cc-scope-level
variable cc-first-block
variable cc-statement-result
variable cc-in-function
variable cc-address-only
variable cc-in-for-declaration
: cc-find ( names count -- index ) L{ names entries }
  entries 0 ?do cc-text names entries 1- i - 32 * + count compare 0= if
    entries 1- i - unloop exit then
  loop -1 ;
: cc-find-symbol cc-symbol-names cc-symbol-count @ cc-find ;
: cc-find-function cc-function-names cc-function-count @ cc-find ;
create cc-alias-names 128 32 * allot
create cc-alias-types 128 allot
create cc-binding-kinds 128 allot
create cc-binding-values 128 cells allot
create cc-alias-levels 128 cells allot
variable cc-alias-count
variable cc-function-aliases
variable cc-storage
create cc-global-state 128 allot
create cc-global-linkage 128 allot
create cc-global-refs 4096 cells allot
variable cc-global-ref-count
variable cc-global-evaluation-level
: cc-global-reference ( alias -- )
  cc-unevaluated @ cc-global-evaluation-level @ > if drop exit then
  cc-global-ref-count @ 4096 >= cc-limit
  cc-global-refs cc-global-ref-count @ cells + ! 1 cc-global-ref-count +! ;
: cc-find-alias-raw cc-alias-names cc-alias-count @ cc-find ;
: cc-find-alias ( -- index ) cc-find-alias-raw cc-find-symbol L{ alias symbol }
  alias 0< if alias exit then
  cc-scope-level @ symbol 0< 0= and if
    cc-symbol-levels symbol cells + @ cc-alias-levels alias cells + @ >=
    if -1 exit then then alias ;
: cc-find-typename cc-find-alias dup 0< 0= if
    dup cc-binding-kinds + c@ if drop -1 then then ;

\ Type IDs: int=0, uint=1, int*=2, void=3, char=4, schar=5,
\ uchar=6, short=7, ushort=8, long=9, ulong=10, bool=11.
create cc-type-sizes 128 cells allot
create cc-type-aligns 128 cells allot
create cc-type-kinds 128 allot
create cc-type-signs 128 allot
create cc-type-ranks 128 allot
create cc-type-bases 128 allot
create cc-type-complete 128 allot
create cc-type-unqualified 128 allot
create cc-type-qualifiers 128 allot
variable cc-initializing
variable cc-static-initializing
create cc-tag-names 128 32 * allot
create cc-tag-types 128 cells allot
variable cc-tag-count
variable cc-tag-scope
variable cc-function-tags
create cc-member-names 256 32 * allot
create cc-member-owners 256 allot
create cc-member-types 256 allot
create cc-member-offsets 256 cells allot
variable cc-member-count
variable cc-type-count
create cc-type-function-shapes 128 cells allot
create cc-prototype-shapes 128 18 * cells allot
variable cc-prototype-count
: cc-init-types
  cc-type-sizes 128 cells 0 fill
  cc-type-kinds 128 0 fill cc-type-signs 128 0 fill
  cc-type-bases 128 0 fill
  cc-type-complete 128 1 fill
  cc-type-qualifiers 128 0 fill
  128 0 do i cc-type-unqualified i + c! loop
  12 cc-type-count !
  0 cc-prototype-count !
  12 0 do 4 cc-type-sizes i cells + ! 3 cc-type-ranks i + c! loop
  1 cc-type-kinds 2 + c! 2 cc-type-kinds 3 + c!
  1 cc-type-sizes 3 cells + !
  1 cc-type-signs c! 1 cc-type-signs 4 + c!
  1 cc-type-signs 5 + c! 1 cc-type-signs 7 + c! 1 cc-type-signs 9 + c!
  7 4 do 1 cc-type-sizes i cells + ! 1 cc-type-ranks i + c! loop
  9 7 do 2 cc-type-sizes i cells + ! 2 cc-type-ranks i + c! loop
  4 cc-type-ranks 9 + c! 4 cc-type-ranks 10 + c!
  1 cc-type-sizes 11 cells + ! 0 cc-type-ranks 11 + c!
  cc-type-sizes cc-type-aligns 128 cells cmove ;
cc-init-types
: cc-unqualified ( type -- type ) cc-type-unqualified + c@ ;
: cc-quals ( type -- mask ) cc-type-qualifiers + c@ ;
: cc-complete ( type -- status ) cc-unqualified cc-type-complete + c@ ;
: cc-size ( type -- bytes ) cc-unqualified cells cc-type-sizes + @ ;
: cc-alignment ( type -- bytes ) cc-unqualified cells cc-type-aligns + @ ;
: cc-kind ( type -- kind ) cc-unqualified cc-type-kinds + c@ ;
: cc-record? ( type -- flag ) cc-kind dup 4 = swap 5 = or ;
: cc-signed? ( type -- flag ) cc-unqualified cc-type-signs + c@ ;
: cc-rank ( type -- rank ) cc-unqualified cc-type-ranks + c@ ;
: cc-pointee ( type -- type ) cc-unqualified cc-type-bases + c@ ;
defer cc-qualify-array
: cc-qualify ( type mask -- type ) 0 L{ type mask result }
  type cc-kind 7 = if type exit then
  type cc-kind 3 = if type mask cc-qualify-array exit then
  type cc-quals mask or 2 (local!) type cc-unqualified 1 (local!)
  mask 0= if type exit then
  cc-type-count @ 0 do i cc-unqualified type = i cc-quals mask = and
    if i unloop exit then loop
  cc-type-count @ dup 128 >= cc-limit 3 (local!) 1 cc-type-count +!
  type cc-type-unqualified result + c! mask cc-type-qualifiers result + c! result ;
: cc-pointer-to ( type -- pointer-type ) 0 L{ base result }
  cc-type-count @ 0 do
    i cc-kind 1 = i cc-pointee base = and if i unloop exit then
  loop
  cc-type-count @ 128 >= cc-limit
  cc-type-count @ 2 (local!)
  4 cc-type-sizes result cells + ! 4 cc-type-aligns result cells + !
  1 cc-type-kinds result + c!
  base cc-type-bases result + c! 1 cc-type-count +! result ;
: cc-width ( type -- bits ) dup cc-kind 2 = if drop 0 else cc-size 8 * then ;
: cc-object ( type -- target )
  dup cc-kind 7 = if s" function is not an object" cc-fail then
  dup cc-record? over cc-kind 6 = or if dup cc-complete 1 <> if
    s" incomplete object type" cc-fail then then
  dup cc-width dup 0= if s" void object unsupported" cc-fail then
  swap cc-alignment 8 * dup 1- cc-data @ + swap negate and cc-data !
  cc-data @ swap cc-data +! cc-data @ 147456 > cc-limit ;
: cc-type ( target -- type )
  dup cc-static-base >= over cc-data-base < and if
    cc-static-base - 8 / cc-static-types + c@ exit then
  dup cc-frame? if cc-data-base - 8 / cc-types + c@ exit then
  dup cc-constant-base >= over 180224 < and if
    cc-constant-base - 32 / cc-constant-types + c@ else drop 0 then ;
: cc-type! ( target type -- ) swap
  dup cc-static-base >= over cc-data-base < and if
    cc-static-base - 8 / cc-static-types + c! exit then
  dup cc-frame? if
    cc-data-base - 8 / cc-types + c! else
    cc-constant-base - 32 / cc-constant-types + c! then ;
: cc-effective-type ( target -- type ) cc-type dup cc-kind 3 = if cc-pointee cc-pointer-to else
  dup cc-kind 7 = if cc-pointer-to then then ;
: cc-pointee-size ( target -- bytes ) cc-effective-type cc-pointee
  dup cc-record? over cc-kind 6 = or if dup cc-complete 1 <> if
    s" arithmetic on incomplete pointer" cc-fail then then
  cc-size dup 0= if s" arithmetic on incomplete pointer" cc-fail then ;
: cc-pointer? ( target -- flag ) cc-effective-type cc-kind 1 = ;
: cc-lvalue ( target -- kind )
  dup cc-static-base >= over cc-data-base < and if drop 1 exit then
  dup cc-frame? if cc-data-base - 8 / cc-lvalues + c@ else drop 0 then ;
: cc-lvalue! ( target kind -- ) swap cc-data-base - 8 / cc-lvalues + c! ;
: cc-lvalue-pointer ( target -- address ) cc-data-base - 8 / cells cc-lvalue-pointers + ;
\ Constant-expression metadata is separate from object storage.
: cc-known? ( source -- flag )
  dup cc-constant-base >= over 180224 < and if drop -1 exit then
  dup cc-frame? if dup cc-lvalue 0= swap cc-data-base - 8 / cc-fold-flags + c@ and else drop 0 then ;
: cc-fold@ ( source -- bits )
  dup cc-frame? if cc-data-base - 8 / cells cc-fold-values + @ else
    cc-constant-base - 32 / cells cc-literal-values + @ then ;
: cc-pointer-origin ( pointer -- origin )
  dup cc-type cc-kind 3 = if
    dup cc-lvalue 2 = if cc-lvalue-pointer @ recurse then exit then
  dup cc-lvalue 0<> if drop 0 exit then
  dup cc-known? if cc-fold@ 8 * exit then
  dup cc-frame? if cc-data-base - 8 / cells cc-pointer-origins + @ else drop 0 then ;
: cc-pointer-origin! ( origin pointer -- ) cc-data-base - 8 / cells cc-pointer-origins + ! ;
: cc-object-origin ( target -- origin )
  dup cc-lvalue 2 = if cc-lvalue-pointer @ cc-pointer-origin then ;
: cc-fold! ( bits target -- )
  cc-data-base - 8 / dup cc-fold-flags + 1 swap c!
  cells cc-fold-values + ! ;
: cc-forget ( target -- ) cc-data-base - 8 / cc-fold-flags + 0 swap c! ;
: cc-fold-convert ( bits type -- bits ) L{ bits type }
  type cc-unqualified 2 (local!)
  type 11 = if bits if 1 else 0 then exit then
  type cc-width dup 32 = if drop bits exit then
  dup 0= if drop 0 exit then
  1 over lshift 1- bits and swap
  type cc-signed? if
    1 over 1- lshift 2 pick and if 1 swap lshift negate or else drop then
  else drop then ;
: cc-fold-load ( source type result -- ) L{ source type result }
  source cc-known? if source cc-fold@ type cc-fold-convert result cc-fold! then ;
: cc-fold-operation ( lhs rhs entry result -- ) 0 0 L{ lhs rhs entry result a b }
  lhs cc-known? rhs cc-known? and 0= if exit then
  lhs cc-fold@ 5 (local!) rhs cc-fold@ 6 (local!)
  entry cc-add-entry @ = if a b + result cc-fold! exit then
  entry cc-sub-entry @ = if a b - result cc-fold! exit then
  entry cc-mul-entry @ = if a b * result cc-fold! exit then
  entry cc-and-entry @ = if a b and result cc-fold! exit then
  entry cc-or-entry @ = if a b or result cc-fold! exit then
  entry cc-xor-entry @ = if a b xor result cc-fold! exit then
  entry cc-not-entry @ = if a invert result cc-fold! exit then
  entry cc-bool-entry @ = if a if 1 else 0 then result cc-fold! exit then
  entry cc-eq-entry @ = if a b = if 1 else 0 then result cc-fold! exit then
  entry cc-lt-entry @ = if a b < if 1 else 0 then result cc-fold! exit then
  entry cc-ult-entry @ = if a b u< if 1 else 0 then result cc-fold! exit then
  entry cc-shl-entry @ = entry cc-shr-entry @ = or entry cc-sar-entry @ = or if
    b 31 u> if exit then
    entry cc-shl-entry @ = if a b lshift else
      a b rshift entry cc-sar-entry @ = a 0< and b 0<> and if
        -1 32 b - lshift or then then result cc-fold! exit
  then
  entry cc-div-entry @ = entry cc-mod-entry @ = or if
    b 0= a -2147483648 = b -1 = and or if exit then
    a abs 0 b abs um/mod
    entry cc-div-entry @ = if nip a 0< b 0< xor else drop a 0< then
    if negate then result cc-fold! exit
  then
  entry cc-udiv-entry @ = entry cc-umod-entry @ = or if
    b 0= if exit then a 0 b um/mod
    entry cc-udiv-entry @ = if nip else drop then result cc-fold! exit
  then ;
' cc-fold-operation is cc-fold-invoke
: cc-fold-invert-body ( source result -- ) L{ source result }
  source cc-known? if source cc-fold@ 1 and 0= if 1 else 0 then result cc-fold! then ;
' cc-fold-invert-body is cc-fold-invert
: cc-load-value ( source type -- value ) cc-cell 0 L{ source type value width }
  type cc-width 4 (local!) value type cc-unqualified cc-type!
  width 32 = if 32 value source cc-op else
    32 value cc-zero @ cc-op width value source cc-op
    type cc-signed? if 32 width do 1 value i + source width 1- + cc-op loop then
  then source type value cc-fold-load
  type cc-kind 1 = source cc-lvalue 0= and if source cc-pointer-origin value cc-pointer-origin! then value ;
defer cc-decay
' cc-raw-value is cc-decay
defer cc-indirect-value
: cc-value ( source -- value ) cc-decay dup cc-type cc-record?
  if s" aggregate value unsupported" cc-fail then
  dup cc-type cc-kind 7 = if s" function value requires call ABI" cc-fail then
  dup cc-type cc-kind 2 = if dup cc-type cc-load-value exit then
  dup cc-lvalue 2 = if cc-indirect-value else dup cc-type cc-load-value then ;
: cc-discard-value ( source -- )
  dup if dup cc-type cc-quals 2 and over cc-lvalue 0<> and if
    dup cc-type cc-kind 3 <> if dup cc-value drop then then then drop ;
: cc-materialize-body ( source -- value )
  cc-decay dup cc-lvalue 2 = if cc-value exit then
  dup cc-lvalue 1 = over cc-type cc-width 32 < and if cc-value then ;
' cc-materialize-body is cc-materialize
: cc-integer-check ( target -- )
  cc-type cc-kind dup 0<> swap 6 <> and if s" expected integer operand" cc-fail then ;
: cc-value-check ( target -- ) cc-effective-type dup cc-record? if
    s" aggregate value unsupported" cc-fail then
  dup cc-kind 7 = if s" function value requires call ABI" cc-fail then
  cc-kind 2 = if s" void value unsupported here" cc-fail then ;
' cc-value-check is cc-check-truth
: cc-promoted ( type -- type )
  cc-unqualified
  dup cc-kind 6 = if cc-pointee exit then
  dup cc-kind 0= over cc-size 4 < and if drop 0 then ;
: cc-common-type ( left right -- type ) cc-type swap cc-type L{ right left }
  right cc-promoted 1 (local!) left cc-promoted 2 (local!)
  right cc-rank left cc-rank < if right left 1 (local!) 2 (local!) then
  right cc-signed? left cc-signed? 0= and if
    right cc-size left cc-size <= if right 1+ exit then
  then right ;
: cc-convert ( source type -- value ) L{ source type }
  type cc-kind 7 = if s" cast to function type" cc-fail then
  type cc-record? if s" aggregate conversion unsupported" cc-fail then
  type cc-kind 3 = if s" array conversion unsupported" cc-fail then
  source cc-decay 1 (local!)
  type cc-kind 2 <> if source cc-value-check then
  source cc-materialize 1 (local!)
  type cc-unqualified 11 = if source cc-truth dup 11 cc-type! else source type cc-load-value then ;
defer cc-types-compatible?
defer cc-query-compatible
defer cc-function-compatible?
: cc-outer-quals ( type -- mask )
  dup cc-kind 3 = if cc-pointee recurse else cc-quals then ;
: cc-pointer-compatible ( left-type right-type -- flag )
  cc-pointee cc-unqualified swap cc-pointee cc-unqualified
  2dup cc-query-compatible >r 3 = swap 3 = or r> or ;
: cc-pointer-assignment? ( destination source -- flag ) L{ destination source }
  destination source cc-pointer-compatible
  source cc-pointee cc-outer-quals destination cc-pointee cc-outer-quals invert and 0= and ;
: cc-composite-pointer ( left right -- type ) 0 L{ left right base }
  left cc-pointee cc-unqualified dup 3 = right cc-pointee cc-unqualified 3 = or
  if drop 3 then 3 (local!)
  base cc-kind 3 = base cc-size 0= and if right cc-pointee cc-unqualified 3 (local!) then
  base left cc-pointee cc-outer-quals right cc-pointee cc-outer-quals or cc-qualify cc-pointer-to ;
: cc-null-constant? ( target -- flag )
  dup cc-known? if dup cc-type cc-kind dup 0= swap 6 = or
    swap cc-fold@ 0= and else drop 0 then ;
: cc-assignment-check ( destination source -- ) L{ destination source }
  destination cc-value-check source cc-value-check
  destination cc-pointer? source cc-pointer? and if
    destination cc-type source cc-effective-type cc-pointer-assignment? if exit then
    s" incompatible pointer types" cc-fail then
  destination cc-pointer? source cc-pointer? = if exit then
  destination cc-pointer? source cc-null-constant? and if exit then
  s" incompatible int and pointer" cc-fail ;
: cc-nest 1 cc-depth +! cc-depth @ 32 > cc-limit ;
: cc-unnest -1 cc-depth +! ;
defer cc-expression
defer cc-full-expression
defer cc-unary
defer cc-inspect
defer cc-read-constant
defer cc-array-suffix
defer cc-string
defer cc-read-record
defer cc-read-enumerators
defer cc-read-abstract-type
defer cc-declarator
defer cc-parameter-declarator
defer cc-prototype
defer cc-function-type-to
: cc-basic-type-start ( -- flag )
  s" int" cc-is s" signed" cc-is or s" unsigned" cc-is or
  s" char" cc-is or s" short" cc-is or s" long" cc-is or
  s" _Bool" cc-is or s" void" cc-is or ;
: cc-typeof-token? s" typeof" cc-is s" __typeof" cc-is or s" __typeof__" cc-is or ;
: cc-const-token? s" const" cc-is s" __const" cc-is or s" __const__" cc-is or ;
: cc-qualifier? cc-const-token? s" volatile" cc-is or
  s" __volatile" cc-is or s" __volatile__" cc-is or ;
: cc-read-qualifiers ( mask -- mask )
  begin cc-qualifier? while cc-const-token? if 1 else 2 then or cc-next repeat ;
: cc-keyword-type? ( -- flag ) cc-basic-type-start cc-typeof-token? or
  s" struct" cc-is or s" union" cc-is or s" enum" cc-is or cc-qualifier? or ;
: cc-type-start ( -- flag ) cc-keyword-type? cc-find-typename 0< 0= or ;
: cc-read-stars ( base -- type )
  begin cc-token @ 42 = while cc-next cc-pointer-to 0 cc-read-qualifiers cc-qualify repeat ;
variable cc-prefix-quals
: cc-read-basic-type 0 0 0 cc-prefix-quals @ L{ saw-int sign base quals }
  cc-basic-type-start cc-qualifier? or 0= if s" expected scalar type" cc-fail then
  begin cc-basic-type-start cc-qualifier? or while
    cc-qualifier? if cc-const-token? if 1 else 2 then quals or 4 (local!) else
    s" int" cc-is if
      saw-int base 4 = or base 11 = or base 3 = or
      if s" conflicting int type" cc-fail then -1 1 (local!)
    else s" signed" cc-is s" unsigned" cc-is or if
      sign if s" conflicting sign specifier" cc-fail then
      s" unsigned" cc-is if 2 else 1 then 2 (local!)
    else
      base if s" conflicting scalar type" cc-fail then
      s" char" cc-is if 4 else s" short" cc-is if 7 else
        s" long" cc-is if 9 else s" _Bool" cc-is if 11 else 3 then then then then
      3 (local!)
      saw-int base 4 = base 11 = or base 3 = or and
      if s" conflicting scalar type" cc-fail then
    then then then cc-next
  repeat
  base 3 = base 11 = or if sign if s" signed void or bool" cc-fail then else
    base 4 = if sign 1 = if 5 3 (local!) else sign 2 = if 6 3 (local!) then then
    else sign 2 = if base 1+ 3 (local!) then then
  then
  base quals cc-qualify dup cc-base-type ! cc-read-stars cc-declared-type ! ;
: cc-read-type 0 cc-read-qualifiers L{ quals }
  cc-find-typename dup 0< 0= if cc-alias-types + c@ cc-next
    quals cc-read-qualifiers cc-qualify dup cc-base-type !
    cc-read-stars cc-array-suffix cc-declared-type ! exit then drop
  s" struct" cc-is s" union" cc-is or s" enum" cc-is or if
    cc-read-record quals cc-read-qualifiers cc-qualify dup cc-base-type ! cc-read-stars cc-array-suffix
    cc-declared-type ! exit then
  cc-typeof-token? if
    cc-next 40 cc-expect cc-nest
    cc-type-start if cc-read-abstract-type else 0 cc-inspect cc-declared-type ! then
    cc-unnest 41 cc-expect cc-declared-type @ quals cc-read-qualifiers cc-qualify dup cc-base-type !
    cc-read-stars cc-array-suffix cc-declared-type !
  else quals cc-prefix-quals ! cc-read-basic-type cc-declared-type @ cc-array-suffix cc-declared-type ! then ;
: cc-name! ( destination -- )
  s" int" cc-is s" void" cc-is or s" if" cc-is or s" else" cc-is or
  s" while" cc-is or s" return" cc-is or s" signed" cc-is or
  s" unsigned" cc-is or s" sizeof" cc-is or s" for" cc-is or
  s" _Alignof" cc-is or s" __alignof" cc-is or s" __alignof__" cc-is or
  s" do" cc-is or s" break" cc-is or s" continue" cc-is or
  s" switch" cc-is or s" case" cc-is or s" goto" cc-is or
  s" _Static_assert" cc-is or s" _Generic" cc-is or s" default" cc-is or s" __builtin_offsetof" cc-is or
  s" __builtin_types_compatible_p" cc-is or
  s" typedef" cc-is or cc-keyword-type? or
  if s" reserved name" cc-fail then
  cc-token @ 2 <> cc-token-size @ 31 > or cc-limit cc-text rot place ;
: cc-symbol-at ( target -- target )
  cc-find-alias-raw dup 0< 0= if cells cc-alias-levels + @ cc-scope-level @ =
    if s" object conflicts with typedef" cc-fail then else drop then
  cc-find-symbol dup 0< 0= if cells cc-symbol-levels + @ cc-scope-level @ =
    if s" duplicate local name" cc-fail then else drop then
  cc-symbol-count @ 128 >= cc-limit
  cc-symbol-names cc-symbol-count @ 32 * + cc-name!
  dup cc-symbol-address cc-symbol-count @ cells + !
  cc-scope-level @ cc-symbol-levels cc-symbol-count @ cells + !
  dup 1 cc-lvalue!
  1 cc-symbol-count +! ;
: cc-symbol ( type -- target ) cc-object cc-symbol-at ;
: cc-fget ( index array -- value ) swap cells + @ ;
: cc-fset ( value index array -- ) swap cells + ! ;
: cc-bind-alias ( type -- ) cc-find-alias-raw cc-find-symbol L{ type alias symbol }
  symbol 0< 0= cc-scope-level @ 0<> and if
    cc-symbol-levels symbol cells + @ cc-scope-level @ = if
      s" typedef conflicts with object" cc-fail then then
  cc-scope-level @ 0= cc-find-function 0< 0= and if
    s" typedef conflicts with function" cc-fail then
  alias 0< 0= if cc-alias-levels alias cells + @ cc-scope-level @ = if
    cc-binding-kinds alias + c@ if s" typedef conflicts with enum constant" cc-fail then
    type cc-alias-types alias + c@ <> if
      s" conflicting typedef" cc-fail then
    type cc-alias-types alias + c! exit then then
  cc-alias-count @ 128 >= cc-limit
  cc-alias-names cc-alias-count @ 32 * + cc-name!
  0 cc-binding-kinds cc-alias-count @ + c!
  type cc-alias-types cc-alias-count @ + c!
  cc-scope-level @ cc-alias-levels cc-alias-count @ cells + ! 1 cc-alias-count +! ;
: cc-bind-enumerator ( value type -- ) L{ value type }
  cc-find-alias-raw dup 0< 0= if cells cc-alias-levels + @ cc-scope-level @ =
    if s" duplicate enum constant" cc-fail then else drop then
  type cc-bind-alias 1 cc-binding-kinds cc-alias-count @ 1- + c!
  value cc-binding-values cc-alias-count @ 1- cells + ! ;
: cc-typedef ( -- ) 0 0 0 0 L{ base type name after }
  cc-next cc-read-type cc-base-type @ 1 (local!) cc-declared-type @ 2 (local!)
  begin type cc-declarator 3 (local!) 2 (local!) cc-token-start @ 4 (local!)
    name cc-pos ! cc-next type cc-bind-alias after cc-pos ! cc-next
    cc-token @ 44 = if cc-next base cc-read-stars 2 (local!) 0 else -1 then
  until 59 cc-expect ;
: cc-param ( fn index -- target ) swap 8 * + cells cc-function-params + @ ;
defer cc-statement
defer cc-increment
defer cc-subscript
defer cc-member
defer cc-block
defer cc-sizeof
defer cc-alignof
defer cc-offsetof
defer cc-compatible
defer cc-generic
create cc-break-fields 128 cells allot
create cc-continue-fields 128 cells allot
variable cc-break-count
variable cc-continue-count
variable cc-loop-level
variable cc-break-level
variable cc-switch-depth
variable cc-statement-expression-depth
variable cc-statement-expression-current
variable cc-statement-expression-count
create cc-statement-expression-parents 513 cells allot
variable cc-label-count
create cc-label-names 128 32 * allot
create cc-label-targets 128 cells allot
create cc-label-regions 128 cells allot
create cc-label-defined 128 allot
variable cc-goto-count
create cc-goto-labels 256 cells allot
create cc-goto-fields 256 cells allot
create cc-goto-regions 256 cells allot
create cc-switch-contexts 32 8 * cells allot
create cc-switch-cases 32 128 * 3 * cells allot
: cc-statement-expression-enter
  cc-statement-expression-count @ 512 >= cc-limit
  1 cc-statement-expression-count +!
  cc-statement-expression-current @
  cc-statement-expression-parents cc-statement-expression-count @ cells + !
  cc-statement-expression-count @ cc-statement-expression-current !
  1 cc-statement-expression-depth +! ;
: cc-statement-expression-leave
  cc-statement-expression-parents cc-statement-expression-current @ cells + @
  cc-statement-expression-current ! -1 cc-statement-expression-depth +! ;

: cc-call ( fn -- value ) 0 L{ fn nargs }
  fn 0< fn cc-function-count @ >= or if s" unknown function" cc-fail then
  fn cc-main-index @ = cc-unevaluated @ 0= and if s" main cannot be called" cc-fail then
  40 cc-expect
  cc-token @ 41 <> if
    begin nargs 8 >= cc-limit cc-expression
      nargs 1+ 2 (local!)
      cc-token @ 44 = if cc-next 0 else -1 then
    until
  then
  41 cc-expect
  nargs fn cc-function-argc cc-fget <> if s" wrong argument count" cc-fail then
  nargs 0 ?do
    dup fn nargs 1- i - cc-param swap cc-assignment-check
    fn nargs 1- i - cc-param cc-type cc-convert
    32 cc-call-args nargs 1- i - 32 * + rot cc-op
  loop
  cc-sp cc-stack-last cc-const cc-eq-entry @ cc-invoke cc-branch >r
  r@ 32 + cc-stack-error-entry @ cc-patch r> cc-current cc-patch
  cc-sp cc-frame-bits cc-const cc-add-entry @ cc-invoke 32 cc-sp rot cc-op
  nargs 0 ?do fn i cc-param dup cc-type cc-width swap cc-call-args i 32 * + cc-op loop
  2 cc-room cc-current cc-layer-bits + cc-const
  24 fn cc-function-return cc-fget rot cc-op
  fn cc-function-entry cc-fget dup if cc-jump else drop
    cc-unevaluated @ 0= if
      cc-call-count @ 128 >= cc-limit
      fn cc-call-functions cc-call-count @ cells + !
      cc-current 18152 + cc-call-fields cc-call-count @ cells + !
      1 cc-call-count +!
    then 0 cc-jump
  then
  32 cc-saved-result fn cc-function-value cc-fget cc-op
  cc-sp cc-frame-bits negate cc-const cc-add-entry @ cc-invoke 32 cc-sp rot cc-op
  cc-cell dup fn cc-function-value cc-fget cc-type cc-unqualified cc-type!
  dup 32 swap cc-saved-result cc-op ;

: cc-address ( target -- pointer )
  dup cc-lvalue 0= if s" address requires lvalue" cc-fail then
  cc-cell L{ target result }
  target cc-lvalue 2 = if
    32 result target cc-lvalue-pointer @ cc-value cc-op
    target cc-lvalue-pointer @ cc-pointer-origin result cc-pointer-origin!
    target cc-lvalue-pointer @ dup cc-known? if cc-fold@ result cc-fold! else drop then
    result target cc-type cc-pointer-to cc-type! result exit then
  target cc-static-base >= target cc-data-base < and if
    32 result target 8 / cc-const cc-op
    target 8 / result cc-fold!
    result target cc-type cc-pointer-to cc-type! result exit then
  32 result target cc-data-base - cc-stack-base + 8 / cc-const cc-op
  10 result 11 + cc-sp 14 + cc-op
  target result cc-pointer-origin!
  result target cc-type cc-pointer-to cc-type! result ;
: cc-decay-body ( source -- pointer )
  dup cc-type cc-kind 7 = if cc-lvalue-pointer @ cc-value exit then
  dup cc-type cc-kind 3 = if
    dup cc-type cc-pointee cc-pointer-to >r
    dup cc-lvalue 2 = if cc-lvalue-pointer @ cc-value else cc-address then
    dup r> cc-type!
  then ;
' cc-decay-body is cc-decay
: cc-pointer-check ( pointer -- ) 0 0 L{ pointer alignment bad }
  pointer cc-pointer? 0= if s" expected pointer" cc-fail then
  pointer cc-type cc-pointee dup cc-kind 2 = if s" dereference of void pointer" cc-fail then
  cc-alignment 2 (local!)
  pointer cc-zero @ cc-pointer-check-entry @ cc-invoke drop
  alignment 1 > if
    cc-cell 3 (local!) 32 bad cc-zero @ cc-op
    1 bad pointer cc-op
    alignment 4 = if bad cc-table-base 24 + bad pointer 1+ cc-lut2 then
    bad cc-branch >r r@ 32 + cc-pointer-error-entry @ cc-patch
    r> cc-current cc-patch
  then ;
: cc-pointer-read ( pointer -- view ) cc-value cc-cell L{ pointer result }
  result pointer cc-type cc-pointee cc-type! result 2 cc-lvalue!
  pointer result cc-lvalue-pointer ! result ;
: cc-pointer-fetch ( pointer -- value ) cc-cell 0 0 L{ pointer result slot type }
  pointer cc-type cc-pointee 4 (local!) result type cc-type!
  type cc-kind 6 = if type cc-complete 1 <> if
    s" value of incomplete enum" cc-fail then then
  result type cc-unqualified cc-type!
  pointer cc-pointer-check
  32 result cc-zero @ cc-op
  2 pointer cc-frame-extra + result cc-frame-extra + cc-room
  cc-slot @ 1+ pointer cc-frame-extra + result cc-frame-extra + 3 (local!)
  21 slot 71 * 50 + pointer cc-op type cc-width result 0 cc-op
  type cc-signed? type cc-width 32 < and if
    32 type cc-width do 1 result i + result type cc-width 1- + cc-op loop
  then result ;
: cc-indirect-value-body ( view -- value ) cc-lvalue-pointer @ cc-pointer-fetch ;
' cc-indirect-value-body is cc-indirect-value
: cc-pointer-write ( pointer value -- ) 0 L{ pointer value slot }
  pointer cc-pointer-check
  2 pointer cc-frame-extra + value cc-frame-extra + cc-room
  cc-slot @ 1+ pointer cc-frame-extra + value cc-frame-extra + 3 (local!)
  21 slot 71 * 26 + pointer cc-op pointer cc-type cc-pointee cc-width 0 value cc-op ;
: cc-static-location ( target -- address )
  dup cc-lvalue 2 = if cc-lvalue-pointer @ dup cc-known? 0= if
    s" unknown static destination" cc-fail then cc-fold@ 8 * then
  dup cc-static-base < over cc-data-base >= or if
    s" invalid static destination" cc-fail then ;
: cc-static-store ( destination source -- value ) L{ destination source }
  cc-initializing @ 0= if s" side effect in static initializer" cc-fail then
  source cc-known? 0= if s" expected static constant initializer" cc-fail then
  source cc-fold@ destination cc-type cc-width destination cc-static-location cc-value! source ;
: cc-lvalue-write ( destination source -- value ) 0 L{ destination source result }
  destination cc-lvalue 0= if s" assignment requires lvalue" cc-fail then
  destination cc-type cc-quals 1 and cc-initializing @ 0= and if
    s" assignment to const object" cc-fail then
  destination cc-type cc-kind 3 = if s" array assignment unsupported" cc-fail then
  destination source cc-assignment-check
  source destination cc-type cc-convert 3 (local!)
  cc-infer-depth @ if result exit then
  cc-static-initializing @ if destination result cc-static-store exit then
  destination cc-lvalue 1 = if destination cc-type cc-width destination result cc-op else
    destination cc-lvalue-pointer @ result cc-pointer-write then
  result cc-forget result ;
: cc-function-description ( fn -- bits ) 512 * cc-function-description-base + ;
: cc-function-designator ( fn -- value ) 0 L{ fn pointer }
  cc-unevaluated @ cc-global-evaluation-level @ <= if
    cc-call-count @ 128 >= cc-limit
    fn cc-call-count @ cc-call-functions cc-fset 0 cc-call-count @ cc-call-fields cc-fset
    1 cc-call-count +! then
  fn cc-function-description 8 / cc-const dup fn cc-function-signatures cc-fget cc-pointer-to cc-type!
  2 (local!) cc-cell dup fn cc-function-signatures cc-fget cc-type!
  dup 2 cc-lvalue! dup pointer swap cc-lvalue-pointer ! ;

: cc-primary ( -- target )
  cc-token @ 34 = if cc-string exit then
  s" _Generic" cc-is if cc-next cc-generic exit then
  s" __builtin_offsetof" cc-is if cc-next cc-offsetof exit then
  s" __builtin_types_compatible_p" cc-is if cc-next cc-compatible exit then
  cc-token @ 40 = if cc-next cc-nest
    cc-token @ 123 = if
      cc-in-function @ 0= if s" statement expression outside function" cc-fail then
      cc-statement-expression-enter cc-block cc-statement-expression-leave
      dup 0= if drop cc-cell dup 3 cc-type! else
        dup cc-type cc-kind 3 = over cc-lvalue 0= or if cc-value dup cc-forget then
      then
    else cc-full-expression then cc-unnest 41 cc-expect exit then
  cc-token @ 1 = if cc-number @ cc-const dup cc-number-type @ cc-type! cc-next exit then
  cc-token @ 2 = if
    cc-find-alias dup 0< 0= if dup cc-binding-kinds + c@ 0= if
      s" typedef used as expression" cc-fail then
      dup cc-binding-kinds + c@ 2 = if
        dup cc-global-reference
        cells cc-binding-values + @ cc-next exit then
      dup cells cc-binding-values + @ cc-const swap cc-alias-types + c@ over swap cc-type!
      cc-next exit then drop
    cc-find-symbol >r cc-find-function >r cc-next
    cc-token @ 40 = if r> r> 0< 0= if s" indirect call unsupported" cc-fail then
      cc-nest cc-call cc-unnest else
      r> r> dup 0< if drop dup 0< if drop s" unknown variable" cc-fail then
        cc-function-designator else swap drop cells cc-symbol-address + @ then then exit
  then s" expected expression" cc-fail ;
: cc-postfix ( -- value )
  cc-primary begin
    cc-token @ dup 46 = swap 266 = or if cc-member else
    cc-token @ 91 = if cc-subscript else
      cc-token @ dup 264 = swap 265 = or if
        cc-token @ cc-next -1 cc-increment else exit then
    then then
  again ;
: cc-unary-body ( -- target )
  s" sizeof" cc-is if cc-next cc-sizeof exit then
  s" _Alignof" cc-is s" __alignof" cc-is or s" __alignof__" cc-is or
  if cc-next cc-alignof exit then
  cc-token @ 40 = if cc-token-start @ >r cc-next cc-type-start if
      cc-read-abstract-type cc-declared-type @ r> drop >r 41 cc-expect
      cc-nest recurse cc-unnest r> cc-convert exit
    then r> cc-pos ! cc-next then
  cc-token @ dup 264 = swap 265 = or if cc-token @ >r cc-next
    cc-nest recurse cc-unnest r> 0 cc-increment exit then
  cc-token @ 38 = if cc-next 1 cc-address-only +!
    cc-nest recurse cc-unnest -1 cc-address-only +! cc-address exit then
  cc-token @ 42 = if cc-next cc-nest recurse cc-unnest cc-pointer-read exit then
  cc-token @ 45 = if cc-next cc-nest recurse cc-unnest
    dup cc-integer-check dup cc-type cc-promoted >r
    cc-zero @ swap cc-sub-entry @ cc-invoke dup r> cc-type! exit then
  cc-token @ 43 = if cc-next cc-nest recurse cc-unnest dup cc-integer-check dup cc-type cc-promoted cc-convert exit then
  cc-token @ 126 = if cc-next cc-nest recurse cc-unnest
    dup cc-integer-check dup cc-type cc-promoted >r
    cc-zero @ cc-not-entry @ cc-invoke dup r> cc-type! exit then
  cc-token @ 33 = if cc-next cc-nest recurse cc-unnest
    cc-truth cc-invert exit then cc-postfix ;
' cc-unary-body is cc-unary
: cc-integer-op ( lhs rhs entry -- value ) L{ lhs rhs entry }
  lhs cc-integer-check rhs cc-integer-check
  lhs rhs cc-common-type >r lhs rhs entry cc-invoke dup r> cc-type! ;
: cc-multiplicative-op ( lhs rhs token -- value ) L{ lhs rhs token }
  lhs rhs token 42 = if cc-mul-entry @ else
    lhs rhs cc-common-type cc-signed? 0= if token 47 = if cc-udiv-entry @ else cc-umod-entry @ then
    else token 47 = if cc-div-entry @ else cc-mod-entry @ then then
  then cc-integer-op ;
: cc-multiplicative ( -- value )
  cc-unary begin cc-token @ dup 42 = over 47 = or swap 37 = or while
    cc-token @ >r cc-next cc-unary r> cc-multiplicative-op repeat ;
: cc-scale-index ( value bytes -- value ) cc-cell L{ value bytes result }
  value cc-integer-check value cc-materialize 1 (local!)
  bytes 1 <> bytes 2 <> and bytes 4 <> and if
    value bytes cc-const cc-mul-entry @ cc-invoke exit then
  bytes 1 = if 32 result value cc-op else
    32 result cc-zero @ cc-op
    bytes 2 = if 31 result 1+ value cc-op else 30 result 2 + value cc-op then
  then value cc-known? if value cc-fold@ bytes * result cc-fold! then result ;
: cc-additive-op ( lhs rhs token -- value ) 0 0 0 L{ lhs rhs token difference result shift }
  lhs cc-pointer? rhs cc-pointer? and if
    token 45 <> if s" cannot add pointers" cc-fail then
    lhs cc-effective-type cc-pointee cc-unqualified rhs cc-effective-type cc-pointee cc-unqualified cc-query-compatible 0= if s" incompatible pointer difference" cc-fail then
    lhs rhs cc-sub-entry @ cc-invoke 4 (local!)
    lhs cc-pointee-size dup 4 = if drop 2 else 2 = if 1 else 0 then then 6 (local!)
    shift 0= if
      lhs cc-pointee-size dup 1 = if drop difference else
        cc-const difference swap cc-div-entry @ cc-invoke then exit
    then
    cc-cell 5 (local!) 32 shift - result difference shift + cc-op
    32 32 shift - do 1 result i + difference 31 + cc-op loop result exit
  then
  lhs cc-pointer? if
    lhs rhs lhs cc-pointee-size cc-scale-index
    token 43 = if cc-add-entry @ else cc-sub-entry @ then
    cc-invoke 5 (local!) result lhs cc-effective-type cc-unqualified cc-type!
    lhs cc-pointer-origin rhs cc-known? and if
      rhs cc-fold@ lhs cc-pointee-size * 8 * token 45 = if negate then
      lhs cc-pointer-origin + result cc-pointer-origin! then result exit
  then
  rhs cc-pointer? if
    token 43 <> if s" cannot subtract pointer from int" cc-fail then
    rhs lhs rhs cc-pointee-size cc-scale-index cc-add-entry @ cc-invoke
    5 (local!) result rhs cc-effective-type cc-unqualified cc-type!
    rhs cc-pointer-origin lhs cc-known? and if
      lhs cc-fold@ rhs cc-pointee-size * 8 * rhs cc-pointer-origin + result cc-pointer-origin! then result exit
  then
  lhs rhs token 43 = if cc-add-entry @ else cc-sub-entry @ then cc-integer-op ;
 : cc-subscript-body ( base -- value )
  cc-next cc-nest cc-full-expression cc-unnest 93 cc-expect
  43 cc-additive-op cc-pointer-read ;
' cc-subscript-body is cc-subscript
: cc-increment-body ( destination token postfix -- value ) 0 L{ destination token postfix old }
  destination cc-lvalue 0= if s" increment requires lvalue" cc-fail then
  postfix if destination cc-value 4 (local!) then
  destination postfix if old else destination then cc-one @
  token 264 = if 43 else 45 then cc-additive-op
  cc-lvalue-write postfix if drop old then ;
' cc-increment-body is cc-increment
: cc-additive ( -- target )
  cc-multiplicative begin cc-token @ dup 43 = swap 45 = or while
    cc-token @ >r cc-next cc-multiplicative r> cc-additive-op repeat ;
: cc-shift-op ( lhs rhs token -- value ) L{ lhs rhs token }
  lhs cc-integer-check rhs cc-integer-check lhs cc-type cc-promoted >r
  lhs rhs token 260 = if cc-shl-entry @ else
    lhs cc-type cc-promoted cc-signed? 0= if cc-shr-entry @ else cc-sar-entry @ then then
  cc-invoke dup r> cc-type! ;
: cc-shift ( -- target )
  cc-additive begin cc-token @ dup 260 = swap 261 = or while
    cc-token @ >r cc-next cc-additive r> cc-shift-op repeat ;
: cc-relational-op ( lhs rhs op -- target ) L{ lhs rhs op }
  lhs cc-value-check rhs cc-value-check
  lhs cc-pointer? rhs cc-pointer? <> if s" incompatible comparison" cc-fail then
  lhs cc-pointer? if lhs cc-effective-type rhs cc-effective-type cc-pointer-compatible 0=
    if s" incompatible comparison pointers" cc-fail then then
  lhs cc-pointer? if cc-ult-entry @ else
    lhs rhs cc-common-type cc-signed? if cc-lt-entry @ else cc-ult-entry @ then then >r
  op 60 = if lhs rhs r> cc-invoke exit then
  op 62 = if rhs lhs r> cc-invoke exit then
  op 258 = if rhs lhs r> cc-invoke cc-invert else
    lhs rhs r> cc-invoke cc-invert then ;
: cc-relational ( -- target )
  cc-shift begin cc-token @ dup 60 = over 62 = or over 258 = or swap 259 = or while
    cc-token @ >r cc-next cc-shift r> cc-relational-op repeat ;
: cc-equality ( -- target )
  cc-relational begin cc-token @ dup 256 = swap 257 = or while
    cc-token @ >r cc-next cc-relational
    dup cc-value-check over cc-value-check
    2dup cc-pointer? swap cc-pointer? and if
      2dup cc-effective-type swap cc-effective-type cc-pointer-compatible 0=
      if s" incompatible comparison pointers" cc-fail then
    then
    2dup cc-pointer? swap cc-pointer? <> if
      2dup cc-null-constant? swap cc-null-constant? or 0=
      if s" incompatible comparison" cc-fail then
    then cc-eq-entry @ cc-invoke
    r> 257 = if cc-invert then repeat ;
: cc-bit-and ( -- value )
  cc-equality begin cc-token @ 38 = while cc-next cc-equality cc-and-entry @ cc-integer-op repeat ;
: cc-bit-xor ( -- value )
  cc-bit-and begin cc-token @ 94 = while cc-next cc-bit-and cc-xor-entry @ cc-integer-op repeat ;
: cc-bit-or ( -- value )
  cc-bit-xor begin cc-token @ 124 = while cc-next cc-bit-xor cc-or-entry @ cc-integer-op repeat ;
: cc-forward ( -- field ) cc-current 18152 + >r 0 cc-jump r> ;
: cc-link! ( field target -- ) cc-unevaluated @ if 2drop exit then swap 24 swap cc-value! ;
defer cc-logical-and
defer cc-conditional
: cc-logical-step ( lhs token -- result ) cc-cell 0 0 0 L{ lhs token result table skip rhs }
  lhs cc-truth cc-branch 4 (local!)
  table token 262 = if 0 else 32 then + cc-current cc-patch
  32 result token 262 = if cc-zero @ else cc-one @ then cc-op
  cc-forward 5 (local!)
  table token 262 = if 32 else 0 then + cc-current cc-patch
  cc-next token 262 = if cc-bit-or else cc-logical-and then cc-truth 6 (local!)
  32 result rhs cc-op skip cc-boundary cc-link!
  lhs cc-known? if
    lhs cc-fold@ 0<> token 262 = xor if
      token 263 = if 1 else 0 then result cc-fold!
    else rhs cc-known? if rhs cc-fold@ result cc-fold! then then
  then result ;
: cc-logical-and-body ( -- value )
  cc-bit-or begin cc-token @ 262 = while 262 cc-logical-step repeat ;
' cc-logical-and-body is cc-logical-and
: cc-logical-or ( -- value )
  cc-logical-and begin cc-token @ 263 = while 263 cc-logical-step repeat ;
: cc-conditional-step ( condition -- result )
    cc-truth dup >r cc-branch cc-cell 0 0 0 r> L{ table result yes no skip condition }
    table 32 + cc-current cc-patch cc-next
    cc-nest cc-full-expression cc-unnest 3 (local!)
    32 result yes cc-materialize cc-op cc-forward 5 (local!)
    58 cc-expect table cc-current cc-patch
    cc-nest cc-conditional cc-unnest 4 (local!) 32 result no cc-materialize cc-op
    yes cc-type cc-kind 2 = no cc-type cc-kind 2 = or if result 3 cc-type! else
    yes cc-pointer? no cc-pointer? <> if
      yes cc-pointer? if no else yes then cc-null-constant? 0=
      if s" incompatible conditional operands" cc-fail then
      result yes cc-pointer? if yes else no then cc-effective-type cc-unqualified cc-type!
    else yes cc-pointer? if
      yes cc-effective-type no cc-effective-type cc-pointer-compatible 0= if s" incompatible conditional pointers" cc-fail then
      result yes cc-effective-type no cc-effective-type cc-composite-pointer cc-type!
    else result yes no cc-common-type cc-type! then then then
    skip cc-boundary cc-link!
    condition cc-known? if
      condition cc-fold@ if yes else no then dup cc-known? if
        cc-fold@ result cc-type cc-fold-convert result cc-fold! else drop then
    then result ;
: cc-conditional-body ( -- result )
  cc-logical-or cc-token @ 63 = if cc-conditional-step then ;
' cc-conditional-body is cc-conditional
: cc-compound-op ( lhs rhs token -- value ) L{ lhs rhs token }
  token 43 = token 45 = or if lhs rhs token cc-additive-op exit then
  token 42 = token 47 = or token 37 = or if lhs rhs token cc-multiplicative-op exit then
  token 260 = token 261 = or if lhs rhs token cc-shift-op exit then
  lhs rhs token 38 = if cc-and-entry @ else
    token 94 = if cc-xor-entry @ else cc-or-entry @ then then cc-integer-op ;
: cc-assignment-step ( destination token -- value ) L{ destination token }
  destination cc-lvalue 0= if s" assignment requires lvalue" cc-fail then
  cc-next cc-nest cc-expression cc-unnest
  token 61 <> if destination swap token 512 - cc-compound-op then
  destination swap cc-lvalue-write ;
: cc-assignment-expression ( -- value )
  cc-conditional cc-token @ dup 61 = swap 512 >= or if
    cc-token @ cc-assignment-step then ;
' cc-assignment-expression is cc-expression
: cc-full-expression-body ( -- value )
  cc-expression cc-token @ 44 = if
    begin cc-discard-value cc-next cc-expression cc-token @ 44 <> until cc-value
    dup cc-forget then ;
' cc-full-expression-body is cc-full-expression
: cc-inspect-body ( unary -- type )
  cc-data @ cc-constants @ cc-call-count @ cc-symbol-count @ 0
  L{ unary data constants calls symbols type }
  1 cc-unevaluated +! cc-nest
  unary 1 = if cc-unary else unary 2 = if cc-expression else cc-full-expression then then
  cc-type 6 (local!)
  cc-unnest -1 cc-unevaluated +!
  data cc-data-base - 8 / cc-data @ data - 8 / >r
  dup cc-types + r@ 0 fill dup cc-fold-flags + r@ 0 fill cc-lvalues + r> 0 fill
  constants cc-constant-base - 32 / cc-constant-types +
  cc-constants @ constants - 32 / 0 fill
  data cc-data ! constants cc-constants ! calls cc-call-count ! symbols cc-symbol-count ! type ;
' cc-inspect-body is cc-inspect
variable cc-constant-type
 : cc-read-constant-body ( -- bits )
  cc-data @ cc-constants @ cc-call-count @ cc-symbol-count @ 0
  L{ data constants calls symbols result }
  1 cc-unevaluated +! cc-nest cc-conditional
  dup cc-integer-check dup cc-known? 0= if s" expected integer constant expression" cc-fail then
  dup cc-type cc-constant-type !
  cc-fold@ 5 (local!) cc-unnest -1 cc-unevaluated +!
  data cc-data-base - 8 / cc-data @ data - 8 / >r
  dup cc-types + r@ 0 fill dup cc-fold-flags + r@ 0 fill cc-lvalues + r> 0 fill
  constants cc-constant-base - 32 / cc-constant-types + cc-constants @ constants - 32 / 0 fill
  data cc-data ! constants cc-constants ! calls cc-call-count ! symbols cc-symbol-count ! result ;
' cc-read-constant-body is cc-read-constant
: cc-array-to ( base count -- type ) 0 0 L{ base length size result }
  base cc-kind 2 = if s" array of void" cc-fail then
  base cc-kind 7 = if s" array of functions" cc-fail then
  base cc-record? base cc-kind 6 = or if base cc-complete 1 <> if
    s" incomplete array element" cc-fail then then
  base cc-size 0= if s" incomplete array element" cc-fail then
  length 0< if s" nonpositive array size" cc-fail then
  length 2097152 base cc-size / u> if s" array size overflow" cc-fail then
  length base cc-size * 3 (local!)
  size 2097152 u> if s" array size overflow" cc-fail then
  cc-type-count @ 0 do
    i cc-kind 3 = i cc-pointee base = and i cc-size size = and
    if i unloop exit then
  loop
  cc-type-count @ 128 >= cc-limit cc-type-count @ 4 (local!)
  3 cc-type-kinds result + c! base cc-type-bases result + c!
  size cc-type-sizes result cells + ! base cc-alignment cc-type-aligns result cells + !
  1 cc-type-count +! result ;
: cc-string-body ( -- view ) cc-static-data @ 0 0 L{ start bytes byte }
  begin
    begin cc-peek 34 <> while
      cc-literal-byte 3 (local!) byte 0< 0= if
        cc-static-data @ 8 + cc-data-base > cc-limit
        byte 8 cc-static-data @ cc-value! 8 cc-static-data +!
        bytes 1+ 2 (local!) then
    repeat cc-step cc-next cc-token @ 34 <>
  until
  cc-static-data @ 8 + cc-data-base > cc-limit
  0 8 cc-static-data @ cc-value! 8 cc-static-data +!
  start 8 / cc-const dup 4 cc-pointer-to cc-type!
  cc-pointer-read dup 4 bytes 1+ cc-array-to cc-type! ;
' cc-string-body is cc-string
: cc-string-size ( -- bytes ) 0 L{ bytes }
  begin
    begin cc-peek 34 <> while
      cc-literal-byte 0< 0= if bytes 1+ 1 (local!) then
    repeat cc-step cc-next cc-token @ 34 <>
  until bytes 1+ ;
: cc-array-suffix-body ( base -- type ) 0 L{ base length }
  cc-token @ 91 = if
    cc-next cc-token @ 93 = if 0 else cc-read-constant dup 1 <
      if s" nonpositive array size" cc-fail then then 2 (local!) 93 cc-expect
    cc-nest base recurse cc-unnest length cc-array-to
  else base then ;
' cc-array-suffix-body is cc-array-suffix
: cc-rewind-temps ( data -- )
  dup cc-data-base - 8 / over cc-data @ swap - 8 / >r
  dup cc-types + r@ 0 fill dup cc-lvalues + r@ 0 fill dup cc-fold-flags + r@ 0 fill
  cells cc-pointer-origins + r> cells 0 fill cc-data ! ;
create cc-declarator-contexts 32 101 * cells allot
variable cc-declarator-depth
variable cc-parameter-name
: cc-declarator-node ( context index -- node ) 2 * 5 + cells + ;
: cc-declarator-add ( context kind argument -- ) L{ context kind argument }
  0 context cc-fget dup 32 >= cc-limit
  context swap cc-declarator-node kind 0 2 pick cc-fset argument 1 rot cc-fset
  0 context cc-fget 1+ 0 context cc-fset ;
: cc-declarator-path ( context -- ) 0 0 0 L{ context start mask group }
  3 context cc-fget 2 (local!)
  begin cc-token @ 42 = while
    cc-next 0 cc-read-qualifiers 3 (local!)
    3 context cc-fget dup 32 >= cc-limit
    69 + cells context + mask swap ! 3 context cc-fget 1+ 3 context cc-fset
  repeat
  cc-token @ 40 = if
    cc-token-start @ 4 (local!) cc-next
    cc-type-start cc-token @ 41 = or 2 context cc-fget 2 <> and if
      group cc-pos ! cc-next else cc-nest context recurse cc-unnest 41 cc-expect then
  else cc-token @ 2 = if
    2 context cc-fget 0= if s" name in abstract declarator" cc-fail then
    1 context cc-fget -1 <> if s" duplicate declarator name" cc-fail then
    cc-token-start @ 1 context cc-fset cc-next
  then then
  begin cc-token @ 91 = cc-token @ 40 = or while
    cc-token @ 91 = if
      cc-next cc-token @ 93 = if 0 else cc-read-constant dup 1 < if
        s" nonpositive array size" cc-fail then then 3 (local!) 93 cc-expect
      context 3 mask cc-declarator-add else context 7 cc-prototype cc-declarator-add then
  repeat
  begin 3 context cc-fget start > while
    3 context cc-fget 1- dup 3 context cc-fset 69 + cells context + @
    context 1 rot cc-declarator-add
  repeat ;
: cc-declarator-parse ( base mode -- type name ) 0 0 L{ base mode context node }
  cc-declarator-depth @ dup 32 >= cc-limit 101 * cells cc-declarator-contexts + 3 (local!)
  context 101 cells 0 fill -1 1 context cc-fset mode 2 context cc-fset
  1 cc-declarator-depth +! context cc-declarator-path
  mode 2 = 1 context cc-fget -1 = and if s" expected declarator name" cc-fail then
  0 context cc-fget begin dup 0> while
    1- context over cc-declarator-node 4 (local!)
    0 node cc-fget 1 = if base cc-pointer-to 1 node cc-fget cc-qualify else
      0 node cc-fget 7 = if base 1 node cc-fget cc-function-type-to else
        base 1 node cc-fget cc-array-to then then 1 (local!)
  repeat drop base 1 context cc-fget -1 cc-declarator-depth +! ;
: cc-declarator-body ( base -- type name ) 2 cc-declarator-parse ;
' cc-declarator-body is cc-declarator
: cc-parameter-declarator-body ( base -- type name ) 1 cc-declarator-parse ;
' cc-parameter-declarator-body is cc-parameter-declarator
: cc-read-abstract-type-body
  cc-read-type cc-token @ 40 = if cc-declared-type @ 0 cc-declarator-parse
    drop cc-declared-type ! then ;
' cc-read-abstract-type-body is cc-read-abstract-type
: cc-prototype-body ( -- shape )
  cc-prototype-count @ dup 128 >= cc-limit 18 * cells cc-prototype-shapes +
  cc-symbol-count @ cc-tag-count @ 256 * cc-tag-scope @ + cc-scope-level @
  cc-alias-count @ cc-data @ 0 0 L{ shape symbols tags scope aliases data type name }
  1 cc-prototype-count +! shape 18 cells 0 fill
  cc-tag-count @ cc-tag-scope ! 1 cc-scope-level +! 40 cc-expect
  cc-token @ 41 <> if 1 1 shape cc-fset then
  begin cc-token @ 41 <> while
    cc-token @ 267 = if
      0 shape cc-fget 0= if s" variadic prototype requires fixed parameter" cc-fail then
      3 1 shape cc-fset cc-next cc-token @ 41 <> if s" expected variadic prototype end" cc-fail then
    else
      cc-nest cc-read-type cc-declared-type @ cc-parameter-declarator cc-unnest
      8 (local!) 7 (local!)
      type cc-kind 2 = if
        0 shape cc-fget 0<> name 0< 0= or cc-token @ 41 <> or if
          s" void parameter unsupported" cc-fail then
      else
        type cc-kind 3 = type cc-kind 7 = or if type cc-pointee
          type cc-kind 7 = if drop type then cc-pointer-to 7 (local!) then
        0 shape cc-fget dup 8 >= cc-limit 2 + shape type cc-unqualified -rot cc-fset
        name 0 shape cc-fget 10 + shape cc-fset 0 shape cc-fget 1+ 0 shape cc-fset
        name 0< 0= if
          cc-token-start @ >r name cc-pos ! cc-next
          cc-cell dup type cc-type! cc-symbol-at drop r> cc-pos ! cc-next then
        cc-token @ 44 = if cc-next cc-token @ 41 = if s" trailing prototype comma" cc-fail then
        else cc-token @ 41 <> if s" expected prototype comma" cc-fail then then
      then
    then
  repeat 41 cc-expect
  symbols cc-symbol-count ! tags 8 rshift cc-tag-count ! tags 255 and cc-tag-scope !
  aliases cc-alias-count ! scope cc-scope-level ! data cc-rewind-temps shape ;
' cc-prototype-body is cc-prototype
: cc-function-type-to-body ( base shape -- type ) 0 0 0 L{ base shape candidate other same }
  base cc-kind dup 3 = swap 7 = or if s" invalid function return type" cc-fail then
  base cc-unqualified 1 (local!)
  cc-type-count @ 0 ?do
    i cc-kind 7 = i cc-pointee base = and if
      i cc-type-function-shapes cc-fget 4 (local!)
      0 shape cc-fget 0 other cc-fget = 1 shape cc-fget 1 other cc-fget = and 5 (local!)
      same if 0 shape cc-fget 0 ?do
        i 2 + shape cc-fget i 2 + other cc-fget <> if 0 5 (local!) then
      loop then same if i unloop exit then
    then
  loop
  cc-type-count @ dup 128 >= cc-limit 3 (local!) 1 cc-type-count +!
  7 cc-type-kinds candidate + c! base cc-type-bases candidate + c!
  1 cc-type-sizes candidate cells + ! 1 cc-type-aligns candidate cells + !
  shape candidate cc-type-function-shapes cc-fset candidate ;
' cc-function-type-to-body is cc-function-type-to
: cc-qualify-array-body ( type mask -- type ) L{ type mask }
  type cc-pointee mask cc-qualify
  type cc-size type cc-pointee cc-size / cc-array-to ;
' cc-qualify-array-body is cc-qualify-array
: cc-find-member ( owner -- index ) L{ owner }
  owner cc-unqualified 1 (local!)
  cc-member-count @ 0 ?do
    cc-member-owners i + c@ owner = if
      cc-text cc-member-names i 32 * + count compare 0= if i unloop exit then
    then
  loop -1 ;
: cc-new-record ( kind -- type ) cc-type-count @ L{ kind type }
  type 128 >= cc-limit 1 cc-type-count +!
  kind cc-type-kinds type + c! 0 cc-type-sizes type cells + !
  1 cc-type-aligns type cells + ! 0 cc-type-complete type + c!
  kind 6 = if 4 cc-type-sizes type cells + ! 4 cc-type-aligns type cells + !
    3 cc-type-ranks type + c! 1 cc-type-bases type + c! then type ;
: cc-read-enumerators-body ( owner -- ) 0 0 0 0 0 0 L{ owner value value-type negative big name after }
  cc-token @ 125 = if s" empty enum" cc-fail then
  begin
    cc-token-start @ 6 (local!) cc-next
    cc-token @ 61 = if cc-next cc-read-constant 2 (local!)
      cc-constant-type @ 3 (local!) else value-type 3 = if
        s" enum increment overflow" cc-fail then then
    value-type cc-signed? value 0< and if -1 4 (local!) else
      value 2147483647 u> if -1 5 (local!) then then
    negative big and if s" 64-bit enum range pending" cc-fail then
    negative if 0 else 1 then cc-type-bases owner + c!
    negative if 1 else 0 then cc-type-signs owner + c!
    cc-token-start @ 7 (local!) name cc-pos ! cc-next
    value value-type cc-signed? value 0< and value 2147483647 u> 0= or
      if 0 else owner then cc-bind-enumerator
    after cc-pos ! cc-next
    cc-token @ 44 = if
      cc-next cc-token @ 125 = if cc-next 1 cc-type-complete owner + c! exit then
      value -1 = value-type cc-signed? 0= and value 2147483647 = or if
        3 3 (local!) 0 2 (local!) else
        value-type cc-signed? value 0< and >r
        value 1+ 2 (local!) r> if 0 else value 0< if 1 else 0 then then 3 (local!) then
    else 125 cc-expect 1 cc-type-complete owner + c! exit then
  again ;
' cc-read-enumerators-body is cc-read-enumerators
: cc-read-members ( owner -- ) 0 0 0 0 0 0 L{ owner base type name after offset slot }
  begin cc-token @ 125 <> while
    cc-token @ 0= if s" unfinished aggregate" cc-fail then
    cc-nest cc-read-type cc-unnest cc-base-type @ 2 (local!)
    cc-declared-type @ 3 (local!)
    begin
      type cc-declarator 4 (local!) 3 (local!) cc-token-start @ 5 (local!)
      type cc-kind 7 = if s" function member unsupported" cc-fail then
      type cc-kind 2 = type cc-size 0= or if s" incomplete member type" cc-fail then
      type cc-record? type cc-kind 6 = or if type cc-complete 1 <> if
        s" incomplete member type" cc-fail then then
      cc-member-count @ dup 256 >= cc-limit 7 (local!)
      name cc-pos ! cc-next owner cc-find-member 0< 0= if s" duplicate member" cc-fail then
      cc-member-names slot 32 * + cc-name!
      after cc-pos ! cc-next
      owner cc-kind 5 = if 0 else owner cc-size
        type cc-alignment dup 1- rot + swap negate and then 6 (local!)
      owner cc-member-owners slot + c! type cc-member-types slot + c!
      offset cc-member-offsets slot cells + ! 1 cc-member-count +!
      offset type cc-size + owner cc-size max cc-type-sizes owner cells + !
      type cc-alignment owner cc-alignment max cc-type-aligns owner cells + !
      cc-token @ 44 = if cc-next base cc-read-stars 3 (local!) 0 else -1 then
    until 59 cc-expect
  repeat cc-next
  owner cc-size owner cc-alignment dup 1- rot + swap negate and
  cc-type-sizes owner cells + ! 1 cc-type-complete owner + c! ;
: cc-read-record-body ( -- type ) 0 0 0 0 0 L{ kind type index name after }
  s" enum" cc-is if 6 else s" union" cc-is if 5 else 4 then then 1 (local!) cc-next
  cc-token @ 2 = if
    cc-tag-names cc-tag-count @ cc-find 3 (local!)
    cc-token-start @ 4 (local!) cc-next cc-token-start @ 5 (local!)
    index 0< index cc-tag-scope @ < cc-token @ dup 123 = swap 59 = or and or if
      cc-in-for-declaration @ if s" tag declaration in for initializer" cc-fail then
      kind cc-new-record 2 (local!)
      cc-tag-count @ 128 >= cc-limit
      name cc-pos ! cc-next
      cc-tag-names cc-tag-count @ 32 * + cc-name!
      type cc-tag-types cc-tag-count @ cells + ! 1 cc-tag-count +!
      after cc-pos ! cc-next
    else index cells cc-tag-types + @ 2 (local!)
      type cc-kind kind <> if s" conflicting aggregate tag" cc-fail then
    then
  else cc-token @ 123 <> if s" expected aggregate tag or body" cc-fail then
    kind cc-new-record 2 (local!) then
  cc-token @ 123 = if
    type cc-complete if s" duplicate aggregate definition" cc-fail then
    2 cc-type-complete type + c!
    cc-next kind 6 = if type cc-read-enumerators else type cc-read-members then then type ;
' cc-read-record-body is cc-read-record
: cc-field-view ( pointer index -- value ) 0 0 L{ pointer index quals result }
  pointer cc-type cc-pointee cc-quals 3 (local!)
  cc-cell 4 (local!) result 6 cc-pointer-to cc-type! 32 result pointer cc-op
  pointer 6 cc-pointer-to result cc-fold-load
  pointer cc-pointer-origin result cc-pointer-origin! result 1 (local!)
  pointer cc-member-offsets index cells + @ cc-const 43 cc-additive-op 1 (local!)
  pointer cc-member-types index + c@ quals cc-qualify cc-pointer-to cc-type!
  pointer cc-pointer-read ;
: cc-member-body ( object -- value ) 0 0 0 L{ object type index pointer }
  cc-token @ 266 = if
    object cc-value 1 (local!)
    object cc-pointer? 0= if s" arrow requires pointer" cc-fail then
    object cc-type cc-pointee 2 (local!) object 4 (local!)
  else object cc-type 2 (local!) object cc-address 4 (local!) then
  type cc-record? 0= if s" member requires aggregate" cc-fail then
  type cc-complete 1 <> if s" incomplete aggregate access" cc-fail then
  cc-next type cc-find-member dup 0< if s" unknown member" cc-fail then 3 (local!) cc-next
  pointer index cc-field-view ;
' cc-member-body is cc-member
: cc-offset-member ( type offset -- type offset ) 0 L{ type offset member }
  type cc-record? 0= if s" offsetof requires aggregate member" cc-fail then
  type cc-complete 1 <> if s" offsetof incomplete aggregate" cc-fail then
  type cc-find-member dup 0< if s" unknown offsetof member" cc-fail then 3 (local!)
  cc-next cc-member-types member + c@ offset cc-member-offsets member cells + @ + ;
: cc-offsetof-body ( -- value ) 0 0 L{ type offset }
  40 cc-expect cc-read-abstract-type cc-declared-type @ 1 (local!) 44 cc-expect
  type offset cc-offset-member 2 (local!) 1 (local!)
  begin
    cc-token @ 46 = if cc-next type offset cc-offset-member 2 (local!) 1 (local!) else
    cc-token @ 91 = if
      type cc-kind 3 <> if s" offsetof index requires array" cc-fail then
      cc-next cc-read-constant type cc-pointee cc-size * offset + 2 (local!)
      type cc-pointee 1 (local!) 93 cc-expect
    else 41 cc-expect offset cc-const dup 1 cc-type! exit then then
  again ;
' cc-offsetof-body is cc-offsetof
: cc-types-compatible-body ( left right -- flag ) L{ left right }
  left cc-quals right cc-quals <> if 0 exit then
  left cc-unqualified 1 (local!) right cc-unqualified 2 (local!)
  left right = if -1 exit then
  left cc-kind 6 = right cc-kind 6 = and if 0 exit then
  left cc-kind 6 = if left cc-complete 0= if 0 exit then left cc-pointee 1 (local!) then
  right cc-kind 6 = if right cc-complete 0= if 0 exit then right cc-pointee 2 (local!) then
  left right = if -1 exit then
  left cc-kind right cc-kind <> if 0 exit then
  left cc-kind 7 = if left right cc-function-compatible? exit then
  left cc-kind 1 = if left cc-pointee right cc-pointee recurse exit then
  left cc-kind 3 = if
    left cc-size right cc-size = left cc-size 0= or right cc-size 0= or
    left cc-pointee right cc-pointee recurse and exit then 0 ;
' cc-types-compatible-body is cc-types-compatible?
: cc-function-compatible-body ( left right -- flag ) 0 0 0 L{ left right first second typed }
  left cc-pointee right cc-pointee cc-types-compatible? 0= if 0 exit then
  left cc-type-function-shapes cc-fget 3 (local!)
  right cc-type-function-shapes cc-fget 4 (local!)
  1 first cc-fget 1 second cc-fget and 1 and if
    0 first cc-fget 0 second cc-fget <> 1 first cc-fget 1 second cc-fget <> or if 0 exit then
    0 first cc-fget 0 ?do
      i 2 + first cc-fget i 2 + second cc-fget cc-types-compatible? 0= if 0 unloop exit then
    loop -1 exit
  then
  1 first cc-fget 1 and if first else second then 5 (local!)
  1 typed cc-fget 2 and if 0 exit then
  0 typed cc-fget 0 ?do
    i 2 + typed cc-fget dup cc-promoted cc-types-compatible? 0= if 0 unloop exit then
  loop -1 ;
' cc-function-compatible-body is cc-function-compatible?
: cc-query-compatible-body ( left right -- flag ) L{ left right }
  left cc-unqualified 1 (local!) right cc-unqualified 2 (local!)
  left cc-kind 3 = right cc-kind 3 = and if
    left cc-size right cc-size = left cc-size 0= or right cc-size 0= or
    left cc-pointee right cc-pointee recurse and exit then
  left right cc-types-compatible? ;
' cc-query-compatible-body is cc-query-compatible
: cc-compatible-body ( -- value )
  40 cc-expect cc-read-abstract-type cc-declared-type @ >r 44 cc-expect
  cc-read-abstract-type cc-declared-type @ r> swap cc-query-compatible
  if 1 else 0 then 41 cc-expect cc-const ;
' cc-compatible-body is cc-compatible
create cc-generic-state 32 14 * cells allot
create cc-generic-types 32 16 * cells allot
variable cc-generic-depth
\ State: default seen/value/start/end/calls-before/calls-after,
\ selected value/start/end/seen, entry jump, association count.
: cc-generic-type ( type context types -- ) L{ type context types }
  type cc-kind 7 = if s" function generic association" cc-fail then
  type cc-kind 2 = type cc-size 0= or if s" incomplete generic association" cc-fail then
  type cc-record? type cc-kind 6 = or if type cc-complete 1 <> if
    s" incomplete generic association" cc-fail then then
  11 context cc-fget dup 16 >= cc-limit
  0 ?do type i types cc-fget cc-types-compatible? if
    s" duplicate compatible generic type" cc-fail then loop
  type 11 context cc-fget types cc-fset
  11 context cc-fget 1+ 11 context cc-fset ;
: cc-generic-emit ( context default -- ) 0 0 L{ context default start value }
  cc-boundary 3 (local!)
  default if cc-call-count @ 4 context cc-fset
    cc-global-ref-count @ 12 context cc-fset then
  cc-nest cc-expression cc-unnest 4 (local!)
  default if value 1 context cc-fset start 2 context cc-fset
    cc-forward 3 context cc-fset cc-call-count @ 5 context cc-fset
    cc-global-ref-count @ 13 context cc-fset
  else value 6 context cc-fset start 7 context cc-fset
    cc-forward 8 context cc-fset 1 9 context cc-fset then ;
: cc-generic-prune ( before after -- ) L{ before after }
  cc-call-count @ after ?do
    cc-call-functions i cells + @ cc-call-functions i after - before + cells + !
    cc-call-fields i cells + @ cc-call-fields i after - before + cells + !
  loop before after - cc-call-count +! ;
: cc-global-prune ( before after -- ) L{ before after }
  cc-global-ref-count @ after ?do
    cc-global-refs i cells + @ cc-global-refs i after - before + cells + !
  loop before after - cc-global-ref-count +! ;
: cc-generic-body ( -- value ) 0 0 0 0 L{ context types control type }
  cc-generic-depth @ dup 32 >= cc-limit
  dup 14 * cells cc-generic-state + 1 (local!)
  16 * cells cc-generic-types + 2 (local!)
  context 14 cells 0 fill 1 cc-generic-depth +!
  40 cc-expect 2 cc-inspect dup cc-kind 3 = if cc-pointee cc-pointer-to else
    dup cc-kind 7 = if cc-pointer-to then then
  cc-unqualified 3 (local!)
  44 cc-expect cc-boundary drop cc-forward 10 context cc-fset
  begin
    s" default" cc-is if
      0 context cc-fget if s" duplicate generic default" cc-fail then
      1 0 context cc-fset cc-next 58 cc-expect
      9 context cc-fget if 2 cc-inspect drop else context -1 cc-generic-emit then
    else
      cc-read-abstract-type cc-declared-type @ 4 (local!)
      type context types cc-generic-type 58 cc-expect
      control type cc-types-compatible? if 9 context cc-fget if
          s" multiple matching generic associations" cc-fail then
        context 0 cc-generic-emit else 2 cc-inspect drop then
    then
    cc-token @ 44 = if cc-next 0 else -1 then
  until 41 cc-expect
  cc-boundary >r
  3 context cc-fget dup if r@ cc-link! else drop then
  8 context cc-fget dup if r@ cc-link! else drop then r> drop
  9 context cc-fget if
    3 context cc-fget if 4 context cc-fget 5 context cc-fget cc-generic-prune
      12 context cc-fget 13 context cc-fget cc-global-prune then
    10 context cc-fget 7 context cc-fget cc-link! 6 context cc-fget
  else 0 context cc-fget 0= if s" no matching generic association" cc-fail then
    10 context cc-fget 2 context cc-fget cc-link! 1 context cc-fget then
  -1 cc-generic-depth +! ;
' cc-generic-body is cc-generic
: cc-hex? ( c -- flag ) dup cc-digit over 65 71 cc-within or
  swap 97 103 cc-within or ;
: cc-assert-message ( -- )
  cc-token @ 34 <> if s" expected assertion string" cc-fail then
  begin cc-token @ 34 = while
    begin cc-peek dup -1 = if s" unfinished assertion string" cc-fail then
      dup 34 <> while
      dup 0= over 10 = or over 13 = or if s" invalid assertion string" cc-fail then
      92 = if cc-step cc-peek -1 = if s" unfinished assertion escape" cc-fail then
        cc-peek 0= if s" invalid assertion escape" cc-fail then
        cc-peek 120 = if cc-step cc-peek cc-hex? 0= if
            s" empty assertion hex escape" cc-fail then
          begin cc-peek cc-hex? while cc-step repeat
        else cc-peek 13 = if cc-step cc-peek 10 = if cc-step then else cc-step then then
      else cc-step then
    repeat drop cc-step cc-next
  repeat ;
: cc-static-assert ( -- )
  cc-next 40 cc-expect cc-read-constant >r
  cc-token @ 44 = if cc-next cc-assert-message then
  41 cc-expect 59 cc-expect r> 0= if s" static assertion failed" cc-fail then ;
: cc-query-type
  cc-token @ 40 = if
    cc-token-start @ >r cc-next cc-type-start if
      cc-read-abstract-type cc-declared-type @ r> drop 41 cc-expect
    else r> cc-pos ! cc-next 1 cc-inspect then
  else 1 cc-inspect then ;
: cc-sizeof-body cc-query-type dup cc-kind 3 = over cc-size 0= and
  if s" sizeof incomplete array" cc-fail then
  dup cc-record? over cc-kind 6 = or if dup cc-complete 1 <> if
    s" sizeof incomplete aggregate" cc-fail then then cc-size cc-const dup 1 cc-type! ;
' cc-sizeof-body is cc-sizeof
: cc-alignof-body cc-query-type dup cc-record? over cc-kind 6 = or if dup cc-complete 1 <> if
    s" alignment of incomplete aggregate" cc-fail then then
  cc-alignment cc-const dup 1 cc-type! ;
' cc-alignof-body is cc-alignof

: cc-return-value ( value -- )
  cc-function-index @ cc-function-value cc-fget cc-type cc-kind 2 = if
    dup cc-type cc-kind 2 <> if s" value returned from void function" cc-fail then
    drop cc-function-index @ cc-function-return cc-fget cc-dynamic exit
  then
  dup cc-function-index @ cc-function-value cc-fget swap cc-assignment-check
  cc-function-index @ cc-function-value cc-fget cc-type cc-convert
  cc-function-index @ cc-main-index @ = if 32 cc-r rot cc-op cc-output-entry @ cc-jump else
    32 cc-function-index @ cc-function-value cc-fget rot cc-op
    cc-function-index @ cc-function-return cc-fget cc-dynamic then ;
: cc-if
  cc-next 40 cc-expect cc-full-expression 41 cc-expect cc-truth cc-branch L{ table }
  table 32 + cc-current cc-patch cc-nest cc-statement cc-unnest
  cc-statement-result @ cc-discard-value
  s" else" cc-is if
    cc-forward >r table cc-current cc-patch cc-next
    cc-nest cc-statement cc-unnest cc-statement-result @ cc-discard-value r> cc-boundary cc-link!
  else table cc-boundary cc-patch then ;
: cc-loop-finish ( continue-target end breaks continues -- ) L{ continue-target end breaks continues }
  cc-break-count @ breaks ?do cc-break-fields i cells + @ end cc-link! loop
  cc-continue-count @ continues ?do cc-continue-fields i cells + @ continue-target cc-link! loop
  breaks cc-break-count ! continues cc-continue-count !
  -1 cc-loop-level +! -1 cc-break-level +! ;
: cc-loop-transfer ( is-continue -- ) L{ is-continue }
  is-continue if cc-loop-level @ else cc-break-level @ then 0= if
    s" loop transfer outside loop or switch" cc-fail then
  cc-next 59 cc-expect
  cc-unevaluated @ if exit then
  is-continue if
    cc-continue-count @ 128 >= cc-limit
    cc-forward cc-continue-fields cc-continue-count @ cells + ! 1 cc-continue-count +!
  else
    cc-break-count @ 128 >= cc-limit
    cc-forward cc-break-fields cc-break-count @ cells + ! 1 cc-break-count +!
  then ;
: cc-while
  cc-next cc-boundary 0 0 0 L{ head table breaks continues }
  40 cc-expect cc-full-expression 41 cc-expect cc-truth cc-branch 2 (local!)
  cc-break-count @ 3 (local!) cc-continue-count @ 4 (local!)
  1 cc-loop-level +! 1 cc-break-level +!
  table 32 + cc-current cc-patch cc-nest cc-statement cc-unnest
  cc-statement-result @ cc-discard-value
  head cc-jump table cc-current cc-patch
  head cc-current breaks continues cc-loop-finish ;
: cc-do
  cc-next cc-boundary 0 cc-break-count @ cc-continue-count @ L{ head condition breaks continues }
  1 cc-loop-level +! 1 cc-break-level +! cc-nest cc-statement cc-unnest
  cc-statement-result @ cc-discard-value
  cc-boundary 2 (local!)
  s" while" cc-is 0= if s" do requires while" cc-fail then
  cc-next 40 cc-expect cc-full-expression 41 cc-expect 59 cc-expect
  cc-truth cc-branch dup 32 + head cc-patch cc-current cc-patch
  condition cc-current breaks continues cc-loop-finish ;
: cc-declarator-type ( base -- type ) cc-read-stars ;
create cc-union-origins 4096 cells allot
create cc-union-members 4096 cells allot
create cc-union-types 4096 cells allot
variable cc-union-count
: cc-union-wipe ( target bytes -- ) 0 L{ target bytes origin }
  cc-union-count @ 0= if exit then target cc-object-origin 3 (local!)
  origin 0= if s" unknown initializer destination" cc-fail then
  cc-union-count @ 0 ?do
    cc-union-origins i cells + @ dup origin >=
    swap cc-union-types i cells + @ cc-size 8 * + origin bytes 8 * + <= and if
      -1 cc-union-members i cells + ! then
  loop ;
: cc-clear-object ( target bytes -- ) L{ target bytes }
  cc-infer-depth @ if exit then
  target bytes cc-union-wipe
  cc-static-initializing @ if target cc-static-location cc-image-base - 8 / cc-image +
    bytes 0 fill exit then
  bytes 0 ?do 8 target i 8 * + cc-zero @ cc-op loop ;
: cc-union-key ( origin type -- slot ) L{ origin type }
  origin 0= if s" unknown initializer destination" cc-fail then
  cc-union-count @ 0 ?do cc-union-origins i cells + @ origin =
    cc-union-types i cells + @ type = and if i unloop exit then loop
  cc-union-count @ 4096 >= cc-limit
  origin cc-union-origins cc-union-count @ cells + !
  type cc-union-types cc-union-count @ cells + !
  -1 cc-union-members cc-union-count @ cells + !
  cc-union-count @ 1 cc-union-count +! ;
: cc-union-slot ( target -- slot ) dup cc-object-origin swap cc-type cc-unqualified cc-union-key ;
: cc-clone-unions ( source destination bytes -- ) 0 0 0
  L{ source destination bytes origin type member }
  cc-infer-depth @ if exit then
  cc-union-count @ 0 ?do
    cc-union-origins i cells + @ 4 (local!) cc-union-types i cells + @ 5 (local!)
    origin source >= origin type cc-size 8 * + source bytes 8 * + <= and if
      cc-union-members i cells + @ 6 (local!)
      member cc-union-members origin source - destination + type cc-union-key cells + ! then
  loop ;
: cc-select-union ( target member -- ) 0 L{ target member slot }
  cc-infer-depth @ if exit then
  target cc-union-slot 3 (local!)
  cc-union-members slot cells + @ member = if exit then
  target target cc-type cc-size cc-clear-object member cc-union-members slot cells + ! ;
variable cc-pending-initializer
: cc-scalar-initializer ( -- value )
  cc-pending-initializer @ if cc-pending-initializer @ 0 cc-pending-initializer ! exit then
  cc-token @ 123 = if cc-next cc-nest recurse cc-unnest
    cc-token @ 44 = if cc-next then 125 cc-expect else cc-expression then ;
: cc-initialize-write ( target value -- value )
  1 cc-initializing ! cc-lvalue-write 0 cc-initializing ! ;
defer cc-initialize-object
defer cc-initialize-tail
defer cc-initialize-range-chain
variable cc-initializer-start
: cc-designator? cc-token @ dup 46 = swap 91 = or ;
: cc-initialize-chain ( target -- )
  dup cc-type cc-kind 3 = if cc-token @ 91 <> if s" expected array designator" cc-fail then else
    dup cc-type cc-record? 0= if s" designator into scalar" cc-fail then
    cc-token @ 46 <> if s" expected member designator" cc-fail then then
  cc-nest cc-initialize-object cc-unnest ;
: cc-initialize-view ( view designated -- ) L{ view designated }
  designated if cc-designator? if view cc-initialize-chain exit then 61 cc-expect then
  view cc-type dup cc-kind 3 = swap cc-record? or if
    view view cc-type cc-size cc-clear-object view cc-initialize-object else
    view cc-scalar-initializer cc-initialize-write drop then ;
: cc-initializer-comma ( braces -- continue )
  if cc-next -1 exit then
  cc-token-start @ >r cc-next
  cc-token @ dup 46 = swap 91 = or if r> cc-pos ! cc-next 0 else r> drop -1 then ;
: cc-member-ordinal ( owner member -- number ) 0 L{ owner member number }
  owner cc-unqualified 1 (local!)
  cc-member-count @ 0 ?do
    cc-member-owners i + c@ owner = if
      i member = if number unloop exit then number 1+ 3 (local!) then
  loop s" unknown initializer member" cc-fail ;
: cc-initialize-string ( target -- ) 0 0 0 0 L{ target source count pointer start }
  target cc-type cc-pointee cc-unqualified dup 4 < swap 6 > or if
    s" string initializer requires character array" cc-fail then
  cc-string 2 (local!) source cc-type cc-size 3 (local!)
  cc-infer-depth @ target cc-infer-target @ = and if
    count cc-infer-length ! exit then
  target cc-type cc-size count 1- < if s" string initializer too long" cc-fail then
  count target cc-type cc-size min 3 (local!)
  cc-infer-depth @ if exit then
  source cc-lvalue-pointer @ cc-fold@ 8 * 5 (local!)
  cc-static-initializing @ if
    start cc-image-base - 8 / cc-image +
    target cc-static-location cc-image-base - 8 / cc-image + count cmove exit then
  target cc-lvalue 1 = if count 8 * target start cc-op exit then
  count 0 ?do
    target cc-decay i cc-const 43 cc-additive-op cc-pointer-read 4 (local!)
    cc-cell dup 4 cc-type! dup 32 swap cc-zero @ cc-op
    dup 8 swap start i 8 * + cc-op pointer swap cc-initialize-write drop
  loop ;
: cc-copy-to-direct ( destination source -- ) 0 0 L{ destination source pointer slot }
  source cc-lvalue 1 = if destination cc-type cc-width destination source cc-op exit then
  source cc-lvalue-pointer @ 3 (local!) pointer cc-pointer-check
  2 pointer cc-frame-extra + destination cc-frame-extra + cc-room
  cc-slot @ 1+ pointer cc-frame-extra + destination cc-frame-extra + 4 (local!)
  21 slot 71 * 50 + pointer cc-op destination cc-type cc-width destination 0 cc-op ;
: cc-range-view ( target index -- view ) cc-const 43 cc-additive-op cc-pointer-read ;
: cc-initialize-range ( target low high -- ) 0 0 0 0
  L{ target low high type seed source data }
  cc-designator? if target low high cc-initialize-range-chain exit then 61 cc-expect
  target cc-type cc-pointee 4 (local!)
  target cc-decay low cc-range-view 6 (local!)
  type cc-kind 3 = type cc-record? or if
    cc-static-initializing @ cc-infer-depth @ 0= and if source 5 (local!) else
      type cc-unqualified cc-object dup type cc-unqualified cc-type! dup 1 cc-lvalue! 5 (local!) then
    cc-token @ 123 = cc-token @ 34 = or if seed 0 cc-initialize-view else
      type cc-kind 3 = if s" array range requires braces or string" cc-fail then
      cc-expression dup cc-type cc-record? if
        dup cc-type cc-unqualified type cc-unqualified cc-types-compatible? 0= if
          s" incompatible aggregate range value" cc-fail then
        cc-static-initializing @ cc-infer-depth @ 0= and if s" nonconstant aggregate range value" cc-fail then
        seed swap cc-copy-to-direct
      else cc-pending-initializer ! seed 0 cc-initialize-view then then
    cc-infer-depth @ if exit then
    cc-data @ 7 (local!)
    high 1+ low ?do
      cc-static-initializing @ if
        seed cc-static-location cc-image-base - 8 / cc-image +
        target cc-static-location i type cc-size 8 * * + cc-image-base - 8 / cc-image + type cc-size cmove
        seed cc-object-origin target cc-object-origin i type cc-size 8 * * + type cc-size cc-clone-unions
      else target cc-decay i cc-range-view 6 (local!)
        source cc-lvalue-pointer @ seed cc-pointer-write
        seed cc-object-origin source cc-object-origin type cc-size cc-clone-unions
      then data cc-rewind-temps
    loop
  else
    cc-scalar-initializer cc-value 5 (local!)
    source seed cc-initialize-write 5 (local!)
    cc-infer-depth @ if exit then cc-data @ 7 (local!)
    high 1+ low 1+ ?do
      cc-static-initializing @ if
        seed cc-fold@ type cc-width target cc-static-location i type cc-size 8 * * + cc-value!
      else target cc-decay i cc-range-view seed cc-initialize-write drop then
      data cc-rewind-temps
    loop
  then ;
: cc-initialize-array ( target -- ) 0 0 0 0 0 0 0 L{ target type index pointer braces designated measuring high }
  target cc-type 2 (local!) cc-token @ 123 = 5 (local!)
  cc-infer-depth @ target cc-infer-target @ = and 7 (local!)
  cc-initializer-start @ 3 (local!) 0 cc-initializer-start !
  braces if cc-next then
  cc-token @ 34 = type cc-pointee cc-kind dup 0= swap 6 = or and index 0= and if target cc-initialize-string
    braces if cc-token @ 44 = if cc-next then 125 cc-expect then exit then
  begin cc-token @ 125 <> cc-pending-initializer @ 0<> or while
    cc-token @ 91 = 6 (local!)
    designated if cc-next cc-read-constant 3 (local!) then
    index 8 (local!)
    designated if cc-token @ 267 = if cc-next cc-read-constant 8 (local!) 2 6 (local!) then 93 cc-expect then
    index 0< if s" negative initializer index" cc-fail then
    high index < if s" reversed initializer range" cc-fail then
    measuring if
      high 2097152 type cc-pointee cc-size / >= cc-limit
      high 1+ cc-infer-length @ max cc-infer-length !
    else high type cc-size type cc-pointee cc-size / >= if
      braces designated or if s" too many array initializers" cc-fail else exit then then
    then
    designated 2 = if target index high cc-initialize-range else
      target cc-decay index cc-const 43 cc-additive-op 4 (local!)
      pointer cc-pointer-read designated cc-initialize-view then
    high 1+ 3 (local!)
    cc-token @ 44 = if
      measuring 0= braces 0= and index type cc-size type cc-pointee cc-size / >= and if exit then
      braces cc-initializer-comma 0= if exit then
    else cc-token @ 125 <> if s" expected initializer comma" cc-fail then then
  repeat braces if cc-next then ;
: cc-member-number ( owner number -- index ) L{ owner number }
  owner cc-unqualified 1 (local!)
  cc-member-count @ 0 ?do
    cc-member-owners i + c@ owner = if
      number 0= if i unloop exit then number 1- 2 (local!)
    then
  loop -1 ;
: cc-initialize-record ( target -- ) 0 0 0 0 0 0 L{ target type number member braces view designated }
  target cc-type 2 (local!) cc-token @ 123 = 5 (local!)
  cc-initializer-start @ 3 (local!) 0 cc-initializer-start !
  braces if cc-next then
  begin cc-token @ 125 <> cc-pending-initializer @ 0<> or while
    cc-token @ 46 = 7 (local!)
    designated if cc-next type cc-find-member 4 (local!)
      member 0< if s" unknown initializer member" cc-fail then
      type member cc-member-ordinal 3 (local!) cc-next
    else type number cc-member-number 4 (local!)
      member 0< type cc-kind 5 = number 0<> and or if
        braces if s" too many aggregate initializers" cc-fail else exit then then then
    type cc-kind 5 = if target member cc-select-union then
    target cc-address member cc-field-view 6 (local!)
    view designated cc-initialize-view
    type cc-kind 5 = cc-infer-depth @ 0= and if member cc-union-members target cc-union-slot cells + ! then
    number 1+ 3 (local!)
    cc-token @ 44 = if
      braces 0= if type number cc-member-number 0< type cc-kind 5 = or if exit then then
      braces cc-initializer-comma 0= if exit then
    else cc-token @ 125 <> if s" expected initializer comma" cc-fail then then
  repeat braces if cc-next then ;
: cc-initialize-object-body ( target -- )
  dup cc-type cc-kind 3 = if cc-initialize-array else cc-initialize-record then ;
' cc-initialize-object-body is cc-initialize-object
: cc-initialize-tail-body ( target start -- ) L{ target start }
  cc-token @ 44 <> if exit then
  target cc-type dup cc-kind 5 = if drop exit then
  dup cc-kind 3 = if cc-size target cc-type cc-pointee cc-size / start <= else
    start cc-member-number 0< then if exit then
  0 cc-initializer-comma if start cc-initializer-start ! target cc-initialize-object then ;
' cc-initialize-tail-body is cc-initialize-tail
create cc-range-paths 32 168 * cells allot
variable cc-range-path-depth
: cc-range-node ( context level -- node ) 5 * 8 + cells + ;
: cc-range-child ( context level parent index -- view ) 0 L{ context level parent index node }
  context level cc-range-node 5 (local!)
  0 node cc-fget 0= if
    parent cc-type cc-kind 3 <> if s" expected array range path" cc-fail then
    1 node cc-fget 0< if s" negative initializer index" cc-fail then
    2 node cc-fget 1 node cc-fget < if s" reversed initializer range" cc-fail then
    parent cc-infer-target @ = cc-infer-depth @ and if
      2 node cc-fget 2097152 parent cc-type cc-pointee cc-size / >= cc-limit else
      2 node cc-fget parent cc-type cc-size parent cc-type cc-pointee cc-size / >= if
        s" too many array initializers" cc-fail then then
    parent cc-decay index cc-range-view
  else
    parent cc-type cc-record? 0= if s" expected member range path" cc-fail then
    parent cc-type cc-kind 5 = if parent 1 node cc-fget cc-select-union then
    parent cc-address 1 node cc-fget cc-field-view
  then ;
: cc-range-restore-parent ( parent node -- ) L{ parent node }
  0 node cc-fget parent cc-type cc-kind 5 = and cc-infer-depth @ 0= and if
    1 node cc-fget cc-union-members parent cc-union-slot cells + ! then ;
: cc-range-last-path ( context -- leaf ) 0 0 L{ context parent node }
  3 context cc-fget 2 (local!)
  0 context cc-fget 0 ?do
    context i cc-range-node 3 (local!) parent 3 node cc-fset
    2 node cc-fget 1+ 4 node cc-fset
    context i parent 2 node cc-fget cc-range-child 2 (local!)
  loop parent ;
: cc-range-write-leaf ( context leaf -- ) 0 0 L{ context leaf seed type }
  1 context cc-fget 3 (local!) 2 context cc-fget 4 (local!)
  type cc-kind 3 = type cc-record? or if
    cc-static-initializing @ if
      seed cc-static-location cc-image-base - 8 / cc-image +
      leaf cc-static-location cc-image-base - 8 / cc-image + type cc-size cmove else
      leaf cc-lvalue-pointer @ seed cc-pointer-write then
    seed cc-object-origin leaf cc-object-origin type cc-size cc-clone-unions
  else leaf seed cc-initialize-write drop then ;
: cc-range-emit-path ( context level parent -- ) 0 0 0 0
  L{ context level parent node low high data }
  level 0 context cc-fget = if context parent cc-range-write-leaf exit then
  context level cc-range-node 4 (local!)
  0 node cc-fget 0= if 1 node cc-fget 5 (local!) 2 node cc-fget 6 (local!) else
    0 5 (local!) 0 6 (local!) then
  high 1+ low ?do
    cc-data @ 7 (local!) context level parent i cc-range-child
    context level 1+ rot recurse parent node cc-range-restore-parent data cc-rewind-temps
  loop ;
: cc-range-freeze ( context leaf -- ) 0 0 L{ context leaf seed type }
  leaf cc-type 4 (local!) type 2 context cc-fset
  type cc-kind 3 = type cc-record? or if
    cc-static-initializing @ cc-infer-depth @ 0= and if leaf 3 (local!) else
      type cc-unqualified cc-object dup type cc-unqualified cc-type! dup 1 cc-lvalue! 3 (local!) then
    cc-token @ 123 = cc-token @ 34 = or if seed 0 cc-initialize-view else
      type cc-kind 3 = if s" array range requires braces or string" cc-fail then
      cc-expression dup cc-type cc-record? if
        dup cc-type cc-unqualified type cc-unqualified cc-types-compatible? 0= if
          s" incompatible aggregate range value" cc-fail then
        cc-static-initializing @ cc-infer-depth @ 0= and if s" nonconstant aggregate range value" cc-fail then
        seed swap cc-copy-to-direct
      else cc-pending-initializer ! seed 0 cc-initialize-view then then
  else cc-scalar-initializer cc-value leaf swap cc-initialize-write 3 (local!) then
  seed 1 context cc-fset ;
: cc-initialize-range-chain-body ( target low high -- ) 0 0 0 0 0
  L{ target low high context parent node member level }
  cc-range-path-depth @ dup 32 >= cc-limit 168 * cells cc-range-paths + 4 (local!)
  context 168 cells 0 fill 1 cc-range-path-depth +!
  target 3 context cc-fset 1 0 context cc-fset
  context 0 cc-range-node 6 (local!) low 1 node cc-fset high 2 node cc-fset
  target 3 node cc-fset high 1+ 4 node cc-fset
  context 0 target low cc-range-child 5 (local!)
  begin cc-designator? while
    0 context cc-fget 8 (local!) level 32 >= cc-limit
    context level cc-range-node 6 (local!) parent 3 node cc-fset
    cc-token @ 46 = if cc-next parent cc-type cc-find-member 7 (local!)
      member 0< if s" unknown initializer member" cc-fail then
      1 0 node cc-fset member 1 node cc-fset
      parent cc-type member cc-member-ordinal dup 2 node cc-fset 1+ 4 node cc-fset cc-next else
      cc-next cc-read-constant dup 1 node cc-fset 2 node cc-fset
      cc-token @ 267 = if cc-next cc-read-constant 2 node cc-fset then 93 cc-expect
      2 node cc-fget 1+ 4 node cc-fset then
    context level parent 1 node cc-fget cc-range-child 5 (local!)
    level 1+ 0 context cc-fset
  repeat 61 cc-expect context parent cc-range-freeze
  0 context cc-fget 0 ?do
    context i cc-range-node dup 3 swap cc-fget swap cc-range-restore-parent
  loop
  cc-infer-depth @ 0= if context 0 target cc-range-emit-path then
  context cc-range-last-path drop
  0 context cc-fget 1- begin dup 0> while
    context over cc-range-node dup 3 swap cc-fget swap 4 swap cc-fget cc-initialize-tail 1-
  repeat drop -1 cc-range-path-depth +! ;
' cc-initialize-range-chain-body is cc-initialize-range-chain
here cc-function-names - constant cc-infer-snapshot-bytes
: cc-infer-array ( type name start -- complete-type )
  cc-data @ cc-constants @ cc-static-data @ cc-infer-target @ cc-infer-length @
  L{ type name start data constants static target length }
  cc-infer-snapshot-bytes allocate dup if s" inference memory exhausted" cc-fail then drop >r
  cc-function-names r@ cc-infer-snapshot-bytes cmove
  1 cc-infer-depth +! 1 cc-unevaluated +!
  name cc-pos ! cc-next cc-cell dup type cc-type! dup cc-infer-target ! cc-symbol-at drop
  0 cc-infer-length ! start cc-pos ! cc-next 61 cc-expect
  cc-token @ 123 <> cc-token @ 34 <> and if s" expected array initializer" cc-fail then
  cc-nest cc-infer-target @ cc-initialize-object cc-unnest
  cc-infer-length @ dup 0= if s" empty inferred array pending" cc-fail then
  -1 cc-infer-depth +! -1 cc-unevaluated +!
  data cc-data-base - 8 / cc-data @ data - 8 / dup >r
  over cc-fold-flags + swap 0 fill cells cc-pointer-origins + r> cells 0 fill
  static cc-image-base - 8 / cc-image + cc-static-data @ static - 8 / 0 fill
  r@ cc-function-names cc-infer-snapshot-bytes cmove r> free if s" inference memory error" cc-fail then
  data cc-data ! constants cc-constants ! static cc-static-data !
  target cc-infer-target ! length cc-infer-length !
  type cc-pointee swap cc-array-to start cc-pos ! cc-next ;
: cc-array-self-view ( target type -- view ) >r cc-address cc-pointer-read dup r> cc-type! ;
: cc-declaration
  cc-read-type cc-base-type @ cc-declared-type @ 0 0 0 cc-in-for-declaration @ 0 0
  L{ base type name after target is-for original symbol }
  cc-token @ 59 = if is-for if s" for initializer requires object declaration" cc-fail then
    cc-next exit then
  begin
    0 7 (local!)
    is-for cc-in-for-declaration !
    type cc-declarator 3 (local!) 2 (local!) cc-token-start @ 4 (local!)
    type cc-kind 2 = if s" void object unsupported" cc-fail then
    type cc-kind 7 = if s" function declaration via declarator pending" cc-fail then
    type cc-kind 3 = type cc-size 0= and if
      cc-token @ 61 <> if s" incomplete array object" cc-fail then
      type 7 (local!) type name after cc-infer-array 2 (local!) then
    name cc-pos ! cc-next type cc-symbol dup type cc-type! 5 (local!)
    after cc-pos ! cc-next
    cc-symbol-count @ 1- 8 (local!)
    original if target original cc-array-self-view cc-symbol-address symbol cells + ! then
    0 cc-in-for-declaration !
    type cc-kind 3 = type cc-record? or if
      target type cc-size cc-clear-object
      cc-token @ 61 = if cc-next cc-token @ 123 <>
        cc-token @ 34 = type cc-kind 3 = and 0= and if
          s" expected aggregate initializer braces" cc-fail then
        target cc-initialize-object then
    else
      cc-token @ 61 = if cc-next cc-scalar-initializer else cc-zero @ then
      target swap cc-initialize-write drop
    then
    target cc-symbol-address symbol cells + !
    cc-token @ 44 = if cc-next base cc-declarator-type 2 (local!) 0 else -1 then
  until 59 cc-expect ;
: cc-for
  cc-symbol-count @ 0 0 0 0 0 cc-tag-count @ 256 * cc-alias-count @ + cc-tag-scope @
  L{ symbols head table step breaks continues tags scope }
  tags 8 rshift cc-tag-scope !
  cc-next 40 cc-expect
  1 cc-scope-level +!
  cc-type-start if 1 cc-in-for-declaration ! cc-declaration else
    cc-token @ 59 <> if cc-full-expression cc-discard-value then 59 cc-expect then
  cc-boundary 2 (local!)
  cc-token @ 59 = if cc-one @ else cc-full-expression cc-truth then
  59 cc-expect cc-branch 3 (local!)
  cc-boundary 4 (local!)
  cc-token @ 41 <> if cc-full-expression cc-discard-value then 41 cc-expect
  head cc-jump table 32 + cc-current cc-patch
  cc-break-count @ 5 (local!) cc-continue-count @ 6 (local!)
  1 cc-loop-level +! 1 cc-break-level +!
  cc-nest cc-statement cc-unnest cc-statement-result @ cc-discard-value step cc-jump
  table cc-current cc-patch step cc-current breaks continues cc-loop-finish
  symbols cc-symbol-count ! tags 8 rshift cc-tag-count ! tags 255 and cc-alias-count !
  scope cc-tag-scope ! -1 cc-scope-level +! ;
: cc-block-body
  cc-symbol-count @ cc-first-block @ cc-tag-count @ cc-tag-scope @ cc-alias-count @
  L{ symbols first tags scope aliases }
  first 0= if tags cc-tag-scope ! then
  0 cc-first-block ! first 0= if 1 cc-scope-level +! then
  0 cc-statement-result ! cc-next begin cc-token @ 125 <> while
    cc-token @ 0= if s" unfinished block" cc-fail then
    cc-nest cc-statement cc-unnest
    cc-token @ 125 <> if cc-statement-result @ cc-discard-value then
  repeat cc-next symbols cc-symbol-count ! tags cc-tag-count ! scope cc-tag-scope !
  aliases cc-alias-count !
  first 0= if -1 cc-scope-level +! then cc-statement-result @ ;
' cc-block-body is cc-block
: cc-switch-context ( -- context )
  cc-switch-depth @ dup 0= if s" case outside switch" cc-fail then
  1- 8 * cells cc-switch-contexts + ;
: cc-switch-row ( context index -- row ) 3 * cells swap 6 swap cc-fget + ;
: cc-switch-less ( left right type -- flag ) cc-signed? if < else u< then ;
: cc-switch-empty? ( low high type -- flag ) >r swap r> cc-switch-less ;
: cc-case ( -- ) 0 0 0 0 0 L{ context low high row type }
  cc-switch-context 1 (local!) 1 context cc-fget 5 (local!)
  7 context cc-fget cc-statement-expression-depth @ <> if
    s" case enters statement expression" cc-fail then
  s" default" cc-is if
    3 context cc-fget -1 <> if s" duplicate default" cc-fail then
    cc-next 58 cc-expect cc-boundary 3 context cc-fset
  else
    cc-next cc-read-constant dup 2 (local!) 3 (local!)
    cc-token @ 267 = if cc-next cc-read-constant 3 (local!) then 58 cc-expect
    low high type cc-switch-empty? 0= if
      5 context cc-fget 0 ?do
        context i cc-switch-row 4 (local!)
        0 row cc-fget 1 row cc-fget type cc-switch-empty? 0= if
          1 row cc-fget low type cc-switch-less 0=
          high 0 row cc-fget type cc-switch-less 0= and if
            s" duplicate or overlapping case" cc-fail then
        then
      loop
    then
    5 context cc-fget dup 128 >= cc-limit context swap cc-switch-row 4 (local!)
    low 0 row cc-fset high 1 row cc-fset cc-boundary 2 row cc-fset
    5 context cc-fget 1+ 5 context cc-fset
  then cc-token @ 125 <> if cc-nest cc-statement cc-unnest then ;
: cc-switch ( -- ) 0 0 0 0 0 0
  L{ value context entry ending row table data }
  cc-next 40 cc-expect cc-full-expression dup cc-integer-check
  dup cc-type cc-promoted cc-convert 1 (local!) 41 cc-expect
  cc-switch-depth @ dup 32 >= cc-limit
  8 * cells cc-switch-contexts + 2 (local!) context 8 cells 0 fill
  value 0 context cc-fset value cc-type 1 context cc-fset
  cc-forward dup 3 (local!) 2 context cc-fset -1 3 context cc-fset
  cc-break-count @ 4 context cc-fset
  cc-switch-depth @ 128 * 3 * cells cc-switch-cases + 6 context cc-fset
  cc-statement-expression-depth @ 7 context cc-fset
  1 cc-switch-depth +! 1 cc-break-level +!
  cc-nest cc-statement cc-unnest cc-statement-result @ cc-discard-value
  cc-forward 4 (local!) entry cc-boundary cc-link!
  cc-data @ 7 (local!)
  5 context cc-fget 0 ?do
    context i cc-switch-row 5 (local!)
    0 row cc-fget 1 row cc-fget 1 context cc-fget cc-switch-empty? 0= if
      0 row cc-fget 1 row cc-fget = if
        value 0 row cc-fget cc-const cc-eq-entry @ cc-invoke
      else
        value 0 row cc-fget cc-const dup value cc-type cc-type! 259 cc-relational-op
        value 1 row cc-fget cc-const dup value cc-type cc-type! 258 cc-relational-op
        cc-and-entry @ cc-invoke
      then cc-branch 6 (local!)
      table 32 + 2 row cc-fget cc-patch table cc-current cc-patch
      data cc-rewind-temps
    then
  loop
  3 context cc-fget dup -1 <> if cc-jump else drop then
  cc-boundary drop ending cc-current cc-link!
  cc-break-count @ 4 context cc-fget ?do cc-break-fields i cells + @ cc-current cc-link! loop
  4 context cc-fget cc-break-count !
  -1 cc-switch-depth +! -1 cc-break-level +! 0 cc-statement-result ! ;
: cc-label? ( -- flag )
  cc-token @ 2 <> if 0 exit then
  cc-token-start @ >r cc-next cc-token @ 58 = r> cc-pos ! cc-next ;
: cc-label-index ( -- index )
  cc-label-names cc-label-count @ cc-find dup 0< if drop
    cc-label-count @ dup 128 >= cc-limit
    dup 32 * cc-label-names + cc-name! 1 cc-label-count +! then ;
: cc-define-label ( -- ) cc-label-index L{ index }
  cc-label-defined index + c@ if s" duplicate label" cc-fail then
  cc-next 58 cc-expect cc-boundary index cc-label-targets cc-fset
  cc-statement-expression-current @ index cc-label-regions cc-fset
  1 cc-label-defined index + c!
  cc-token @ 125 <> if cc-nest cc-statement cc-unnest then ;
: cc-goto ( -- ) cc-next
  cc-token @ 2 <> if s" expected label name" cc-fail then cc-label-index L{ index }
  cc-next 59 cc-expect cc-goto-count @ 256 >= cc-limit
  index cc-goto-count @ cc-goto-labels cc-fset
  cc-statement-expression-current @ cc-goto-count @ cc-goto-regions cc-fset
  cc-unevaluated @ if 0 else cc-forward then cc-goto-count @ cc-goto-fields cc-fset
  1 cc-goto-count +! ;
: cc-goto-finish ( -- ) 0 0 0 L{ index source target }
  cc-goto-count @ 0 ?do
    i cc-goto-labels cc-fget 1 (local!)
    cc-label-defined index + c@ 0= if s" undefined label" cc-fail then
    i cc-goto-regions cc-fget 2 (local!) index cc-label-regions cc-fget 3 (local!)
    begin source target <> source 0<> and while
      source cc-statement-expression-parents cc-fget 2 (local!)
    repeat source target <> if s" goto enters statement expression" cc-fail then
    i cc-goto-fields cc-fget dup if index cc-label-targets cc-fget cc-link! else drop then
  loop ;
: cc-label-reset
  0 cc-label-count ! cc-label-defined 128 0 fill 0 cc-goto-count !
  0 cc-statement-expression-current ! 0 cc-statement-expression-count ! ;
: cc-statement-body
  0 cc-statement-result !
  s" case" cc-is s" default" cc-is or if cc-case exit then
  cc-label? if cc-define-label exit then
  s" typedef" cc-is if cc-typedef exit then
  s" _Static_assert" cc-is if cc-static-assert exit then
  cc-token @ 123 = if
    cc-block cc-discard-value 0 cc-statement-result ! exit then
  cc-type-start if cc-declaration 0 cc-statement-result ! exit then
  s" if" cc-is if cc-if 0 cc-statement-result ! exit then
  s" switch" cc-is if cc-switch exit then
  s" goto" cc-is if cc-goto exit then
  s" while" cc-is if cc-while 0 cc-statement-result ! exit then
  s" do" cc-is if cc-do 0 cc-statement-result ! exit then
  s" for" cc-is if cc-for 0 cc-statement-result ! exit then
  s" break" cc-is if 0 cc-loop-transfer exit then
  s" continue" cc-is if -1 cc-loop-transfer exit then
  s" return" cc-is if cc-next
    cc-token @ 59 = if
      cc-function-index @ cc-function-value cc-fget cc-type cc-kind 2 <>
      if s" empty return from nonvoid function" cc-fail then
      cc-cell dup 3 cc-type!
    else cc-full-expression then 59 cc-expect cc-return-value
    0 cc-statement-result ! exit then
  cc-token @ 59 = if cc-next exit then
  cc-full-expression cc-statement-result ! 59 cc-expect ;
' cc-statement-body is cc-statement
: cc-register-function-signature ( fn -- ) 0 L{ fn shape }
  cc-prototype-count @ dup 128 >= cc-limit 18 * cells cc-prototype-shapes + 2 (local!)
  1 cc-prototype-count +! shape 18 cells 0 fill
  fn cc-function-argc cc-fget 0 shape cc-fset cc-function-prototyped @ 1 shape cc-fset
  fn cc-function-argc cc-fget 0 ?do
    fn i cc-param cc-type cc-unqualified i 2 + shape cc-fset
    -1 i 10 + shape cc-fset
  loop
  fn cc-function-value cc-fget cc-type shape cc-function-type-to
  fn cc-function-signatures cc-fset ;
: cc-store-function-descriptions ( -- ) 0 L{ description }
  cc-function-count @ 0 ?do
    i cc-function-description 1 (local!)
    i cc-function-entry cc-fget 32 description cc-value!
    i cc-function-return cc-fget cc-data-base - 32 description 32 + cc-value!
    i cc-function-value cc-fget cc-data-base - 32 description 64 + cc-value!
    i cc-function-argc cc-fget 0 ?do
      j i cc-param cc-data-base - 32 description i 3 + 32 * + cc-value!
    loop
  loop ;
: cc-function
  cc-token @ 59 = if cc-next exit then
  cc-function-type @ cc-kind dup 3 = swap 7 = or if s" invalid function return type" cc-fail then
  cc-function-type @ cc-record? if s" aggregate return unsupported" cc-fail then
  cc-find-alias-raw 0< 0= if s" function conflicts with ordinary name" cc-fail then
  cc-alias-count @ cc-function-aliases !
  cc-tag-count @ cc-function-tags ! cc-tag-count @ cc-tag-scope !
  cc-find-function dup -1 = if drop
    -1 cc-new-function !
    cc-function-count @ dup cc-function-index ! 16 >= cc-limit
    cc-storage @ 2 = if 1 else 0 then cc-function-linkage cc-function-index @ + c!
    cc-function-names cc-function-index @ 32 * + cc-name!
    0 cc-function-index @ cc-function-entry cc-fset
    cc-cell cc-function-index @ cc-function-return cc-fset
    cc-cell dup cc-function-type @ cc-type!
    cc-function-index @ cc-function-value cc-fset
    0 cc-function-index @ cc-function-argc cc-fset
    1 cc-function-count +!
  else cc-function-index ! 0 cc-new-function !
    cc-storage @ 2 = cc-function-linkage cc-function-index @ + c@ 0= and if
      s" conflicting function linkage" cc-fail then
    cc-function-index @ cc-function-value cc-fget cc-type cc-unqualified cc-function-type @ cc-unqualified <>
    if s" conflicting function return type" cc-fail then
  then
  s" main" cc-is if cc-function-index @ cc-main-index ! then
  0 cc-symbol-count ! 0 cc-parameter-count ! 1 cc-scope-level ! cc-next 40 cc-expect
  cc-token @ 41 <> if 1 else 0 then cc-function-prototyped !
  cc-token @ 41 <> if
      begin
        cc-read-type
        cc-declared-type @ cc-parameter-declarator cc-parameter-name ! cc-declared-type !
        cc-token-start @ cc-parameter-after !
        cc-declared-type @ cc-kind 2 = if
          cc-parameter-count @ 0= cc-token @ 41 = and cc-parameter-name @ 0< and 0=
          if s" void parameter unsupported" cc-fail then -1
        else
        cc-declared-type @ dup cc-kind 3 = if cc-pointee cc-pointer-to else
          dup cc-kind 7 = if cc-pointer-to then then cc-declared-type !
        cc-declared-type @ cc-record? if s" aggregate parameter unsupported" cc-fail then
        cc-parameter-count @ dup 8 >= cc-limit >r
        cc-new-function @ if
          cc-declared-type @ cc-object dup cc-declared-type @ cc-type!
          dup cc-function-index @ 8 * r@ + cells cc-function-params + !
        else
          r@ cc-function-index @ cc-function-argc cc-fget >=
          if s" conflicting prototype" cc-fail then
          cc-function-index @ r@ cc-param
          dup cc-type cc-unqualified cc-declared-type @ cc-unqualified <>
          if s" conflicting parameter type" cc-fail then
          dup cc-declared-type @ cc-type!
        then
        cc-parameter-name @ 0< if drop else cc-parameter-name @ cc-pos ! cc-next
          cc-symbol-at drop cc-parameter-after @ cc-pos ! cc-next then
        r> 1+ cc-parameter-count !
        cc-token @ 44 = if cc-next 0 else -1 then
        then
      until
  then 41 cc-expect
  cc-new-function @ if
    cc-parameter-count @ cc-function-index @ cc-function-argc cc-fset
  else cc-parameter-count @ cc-function-index @ cc-function-argc cc-fget <>
    if s" conflicting prototype" cc-fail then
  then
  cc-function-index @ cc-register-function-signature
  cc-token @ 59 = if cc-next cc-function-tags @ cc-tag-count ! 0 cc-tag-scope !
    cc-function-aliases @ cc-alias-count ! 0 cc-symbol-count ! 0 cc-scope-level ! exit then
  cc-function-index @ cc-function-entry cc-fget
  if s" duplicate function definition" cc-fail then
  cc-symbol-count @ cc-parameter-count @ <>
  if s" parameter name missing in definition" cc-fail then
  cc-boundary cc-function-index @ cc-function-entry cc-fset
  cc-function-index @ cc-main-index @ = if
    cc-function-type @ cc-unqualified if s" main must return int" cc-fail then
    cc-function-index @ cc-function-argc cc-fget 0<> if s" main takes no parameters" cc-fail then
  then
  cc-token @ 123 <> if s" expected function body" cc-fail then
  cc-label-reset
  -1 cc-first-block !
  -1 cc-in-function ! cc-statement 0 cc-in-function !
  cc-goto-finish
  cc-function-type @ cc-kind 2 = if cc-cell dup 3 cc-type! else cc-zero @ then cc-return-value
  cc-function-tags @ cc-tag-count ! 0 cc-tag-scope !
  cc-function-aliases @ cc-alias-count ! 0 cc-symbol-count ! 0 cc-scope-level ! ;

: cc-static-expression ( target -- bits )
  cc-data @ cc-constants @ cc-call-count @ cc-symbol-count @ 0 cc-global-evaluation-level @
  L{ target data constants calls symbols result level }
  1 cc-unevaluated +! cc-unevaluated @ cc-global-evaluation-level ! cc-nest
  cc-conditional cc-value dup target swap cc-assignment-check
  target cc-type cc-convert
  dup cc-known? 0= if s" expected static constant initializer" cc-fail then
  cc-fold@ 6 (local!) cc-unnest -1 cc-unevaluated +! level cc-global-evaluation-level !
  data cc-data-base - 8 / cc-data @ data - 8 / >r
  dup cc-types + r@ 0 fill dup cc-fold-flags + r@ 0 fill cc-lvalues + r> 0 fill
  constants cc-constant-base - 32 / cc-constant-types + cc-constants @ constants - 32 / 0 fill
  data cc-data ! constants cc-constants ! symbols cc-symbol-count ! result ;
: cc-static-scalar ( target -- value )
  cc-token @ 123 = if cc-next cc-nest recurse cc-unnest
    cc-token @ 44 = if cc-next then 125 cc-expect else cc-static-expression then ;
: cc-static-aggregate ( target alias original -- )
  cc-data @ cc-constants @ cc-call-count @ cc-symbol-count @ cc-global-evaluation-level @
  L{ target alias original data constants calls symbols level }
  1 cc-unevaluated +! cc-unevaluated @ cc-global-evaluation-level !
  original if target original cc-array-self-view cc-binding-values alias cells + ! then
  1 cc-static-initializing ! target target cc-type cc-size cc-clear-object
  cc-token @ 123 <> cc-token @ 34 = target cc-type cc-kind 3 = and 0= and if
    s" expected aggregate initializer braces" cc-fail then
  cc-nest target cc-initialize-object cc-unnest 0 cc-static-initializing !
  target cc-binding-values alias cells + !
  -1 cc-unevaluated +! level cc-global-evaluation-level !
  data cc-data-base - 8 / cc-data @ data - 8 / >r
  dup cc-types + r@ 0 fill dup cc-fold-flags + r@ 0 fill cc-lvalues + r> 0 fill
  constants cc-constant-base - 32 / cc-constant-types + cc-constants @ constants - 32 / 0 fill
  data cc-data ! constants cc-constants ! symbols cc-symbol-count ! ;
: cc-global-array-type ( type name after -- type ) L{ type name after }
  name cc-pos ! cc-next cc-find-alias-raw dup 0< 0= if
    dup cc-binding-kinds + c@ 2 = if cc-alias-types + c@ dup type cc-types-compatible? if
      after cc-pos ! cc-next exit then drop else drop then else drop then
  after cc-pos ! cc-next type ;
: cc-global ( -- ) cc-base-type @ cc-declared-type @ 0 0 0 0 0 0
  L{ base type name after target value alias original }
  begin
    0 8 (local!)
    type cc-declarator 3 (local!) 2 (local!) cc-token-start @ 4 (local!)
    type cc-kind 2 = if s" void global object" cc-fail then
    type cc-kind 7 = if s" function declaration via declarator pending" cc-fail then
    type cc-record? type cc-kind 6 = or if type cc-complete 1 <> if
      s" incomplete global object" cc-fail then then
    type cc-kind 3 = type cc-size 0= and if
      type name after cc-global-array-type 2 (local!)
      type cc-size 0= if
        cc-token @ 61 <> if s" incomplete global array pending" cc-fail then
        type 8 (local!) type name after cc-infer-array 2 (local!) then then
    name cc-pos ! cc-next
    cc-find-alias-raw 7 (local!)
    cc-find-function 0< 0= if s" global object conflicts with function" cc-fail then
    alias 0< if
      type cc-alignment 8 * dup 1- cc-static-data @ + swap negate and cc-static-data !
      cc-static-data @ 5 (local!) type cc-width cc-static-data +!
      cc-static-data @ cc-data-base > cc-limit target type cc-type!
      type cc-bind-alias cc-alias-count @ 1- 7 (local!)
      2 cc-binding-kinds alias + c! 0 cc-global-state alias + c!
      cc-storage @ 2 = if 1 else 0 then cc-global-linkage alias + c!
      target cc-binding-values alias cells + !
    else
      cc-binding-kinds alias + c@ 2 <> if s" global conflicts with ordinary name" cc-fail then
      cc-storage @ 1 <> if
        cc-storage @ 2 = if 1 else 0 then cc-global-linkage alias + c@ <> if
          s" conflicting global linkage" cc-fail then then
      type cc-alias-types alias + c@ cc-types-compatible? 0= if s" conflicting global type" cc-fail then
      cc-binding-values alias cells + @ 5 (local!)
      target type cc-type! type cc-alias-types alias + c!
    then
    after cc-pos ! cc-next
    cc-token @ 61 = if
      cc-global-state alias + c@ 2 = if s" duplicate global definition" cc-fail then
      cc-next type cc-kind 3 = type cc-record? or if target alias original cc-static-aggregate else
        target cc-static-scalar 6 (local!) value type cc-width target cc-value! then
      2 cc-global-state alias + c!
    else cc-storage @ 1 <> cc-global-state alias + c@ 0= and if
      1 cc-global-state alias + c! then then
    cc-token @ 44 = if cc-next base cc-declarator-type 2 (local!) 0 else -1 then
  until 59 cc-expect ;
: cc-external ( -- ) 0 0 L{ name simple-name }
  0 cc-storage ! s" extern" cc-is if 1 cc-storage ! cc-next then
  s" static" cc-is if cc-storage @ if s" conflicting storage classes" cc-fail then
    2 cc-storage ! cc-next then
  cc-read-type cc-declared-type @ cc-function-type !
  cc-token @ 59 = if cc-next exit then
  cc-token @ 2 = 2 (local!) cc-token-start @ 1 (local!) cc-next
  cc-token @ 40 = simple-name and if name cc-pos ! cc-next cc-function else
    name cc-pos ! cc-next cc-global then ;

: cc-finish
  cc-global-ref-count @ 0 ?do
    cc-global-refs i cells + @ cc-global-state + c@ 0= if
      s" referenced extern object has no definition" cc-fail then
  loop
  cc-main-index @ 0< if s" main missing" cc-fail then
  cc-main-index @ cc-function-entry cc-fget 0=
  if s" main definition missing" cc-fail then
  cc-call-count @ 0 ?do
    cc-call-functions i cells + @ cc-function-entry cc-fget
    dup 0= if s" referenced function has no definition" cc-fail then
    cc-call-fields i cells + @ dup if swap cc-link! else 2drop then
  loop
  cc-store-function-descriptions
  cc-main-index @ cc-function-entry cc-fget 32 64 cc-guard-constants cc-bits!
  cc-current cc-image-base - 2 * 32 0 cc-guard-constants cc-bits! ;
: cc-export
  cc-prelude cc-prelude-bytes @ dup >r cs-write r> <> if 1 cs-exit then
  cc-guard-data cc-guard-constants 36 cc-install
  cc-record 37 0 fill
  24 cc-load-status 118 0 cc-record cc-row-at
  cc-current cc-image-base - cc-image-base 0 71 cc-record cc-row-at
  cc-layer-bits 0 cc-guard-code 213 cc-record cc-row-at
  cc-record 37 cs-write 37 <> if 1 cs-exit then
  cc-image cc-current cc-image-base - 8 / dup >r cs-write r> <> if 1 cs-exit then ;
: cc-read-source
  0 cc-length !
  begin cc-source cc-length @ + cc-source-max 1+ cc-length @ - cs-read
    dup 0< if drop s" input error" cc-fail then
    dup 0= if drop exit then cc-length +!
    cc-length @ cc-source-max > cc-limit
  again ;
: CC-RUN
  0 cc-pos ! 0 cc-token-start ! 0 cc-depth ! 0 cc-function-count ! 0 cc-call-count !
  cc-function-description-base cc-image-base - 8 / cc-image + 1024 0 fill
  0 cc-loop-level ! 0 cc-break-level ! 0 cc-switch-depth !
  0 cc-statement-expression-depth !
  cc-label-reset
  0 cc-break-count ! 0 cc-continue-count !
  0 cc-scope-level ! 0 cc-first-block !
  0 cc-unevaluated !
  0 cc-in-function !
  0 cc-address-only !
  0 cc-in-for-declaration !
  0 cc-generic-depth !
  0 cc-initializing !
  0 cc-pending-initializer !
  0 cc-initializer-start ! 0 cc-range-path-depth ! 0 cc-declarator-depth !
  0 cc-infer-depth ! 0 cc-infer-target ! 0 cc-infer-length !
  0 cc-static-initializing !
  0 cc-union-count ! cc-pointer-origins 2048 cells 0 fill
  0 cc-alias-count ! 0 cc-symbol-count !
  0 cc-global-ref-count ! cc-global-state 128 0 fill
  0 cc-global-evaluation-level !
  -1 cc-main-index ! cc-data-base cc-data !
  cc-static-base cc-static-data !
  cc-static-types 4096 0 fill cc-image 4096 0 fill
  cc-init-types cc-fold-flags 2048 0 fill cc-types 2048 0 fill
  0 cc-tag-count ! 0 cc-tag-scope ! 0 cc-member-count !
  cc-lvalues 2048 0 fill
  cc-constant-types 512 0 fill
  cc-code-base cc-origin ! cc-image-base cc-emission-base ! cc-image cc-emission-buffer !
  cc-library-layer @ cc-layer ! 3 cc-slot !
  cc-library-constants @ cc-constants !
  cc-read-source cc-next begin cc-token @ while
    s" typedef" cc-is if cc-typedef else
    s" _Static_assert" cc-is if cc-static-assert else cc-external then then repeat
  cc-finish cc-export 0 cs-exit ;
