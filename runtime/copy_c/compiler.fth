\ C subset compiler. All source parsing and target emission run in Forth.
\ Target bit addresses; int values use LSB-first fields in MSB-first bytes.
decimal
8192 constant cc-source-max
64 constant cc-layer-max
18176 constant cc-layer-bits
2272 constant cc-layer-bytes
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
: cc-fail ( addr len -- )
  ." copy-c error at byte " cc-token-start @ . type cr 2 cs-exit ;
: cc-limit ( flag -- ) if s" capacity exceeded" cc-fail then ;

create cc-image 16384 cc-layer-max cc-layer-bytes * + allot
cc-image 16384 cc-layer-max cc-layer-bytes * + 0 fill
create cc-record 37 allot
create cc-reversed 256 allot
: cc-prepare-reverse
  256 0 do 0 i 8 0 do swap 2 * over 1 and + swap 1 rshift loop
    drop cc-reversed i + c! loop ;
cc-prepare-reverse

: cc-bits! ( value width position buffer -- )
  0 0 0 L{ value width position buffer part shift mask }
  begin width while
    8 position 7 and - width min 5 (local!)
    8 position 7 and - part - 6 (local!)
    1 part lshift 1- shift lshift 7 (local!)
    buffer position 3 rshift + dup c@ mask invert and
    value 255 and cc-reversed + c@ position 7 and rshift mask and or swap c!
    value part rshift 1 (local!)
    position part + 3 (local!) width part - 2 (local!)
  repeat ;
: cc-value! ( value bits target -- ) cc-data-base - cc-image cc-bits! ;

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
  cc-emission-base @ - cc-emission-buffer @ cc-row-at ;

variable cc-layer
variable cc-slot
variable cc-constants
variable cc-data
variable cc-origin
: cc-current ( -- target ) cc-layer @ cc-layer-bits * cc-origin @ + ;
: cc-new 1 cc-layer +! cc-layer @ cc-layer-max >= cc-limit 3 cc-slot ! ;
: cc-end ( target -- )
  cc-layer-bits 0 rot cc-current 255 71 * + cc-row ;
: cc-jump ( target -- ) cc-end cc-new ;
: cc-room ( count -- ) cc-slot @ + 255 > if
    cc-current cc-layer-bits + cc-jump then ;
: cc-op ( n dst src -- )
  1 cc-room cc-current cc-slot @ 71 * + cc-row 1 cc-slot +! ;
: cc-boundary ( -- target )
  cc-slot @ 3 <> if cc-current cc-layer-bits + cc-jump then cc-current ;
: cc-cell ( -- target )
  cc-data @ 32 cc-data +! cc-data @ 147456 > cc-limit ;
: cc-const ( value -- target )
  cc-constants @ 32 cc-constants +!
  cc-constants @ 180224 > cc-limit >r 32 r@ cc-value! r> ;
: cc-patch ( target value -- ) swap 32 swap cc-value! ;
: cc-dynamic ( source -- )
  1 cc-room 24 18152 rot cc-op 0 cc-jump ;

\ Patch the active instruction, then perform its LUT read in the same tick.
: cc-lut1 ( dst base a -- ) L{ dst base a }
  2 cc-room 1 cc-slot @ 1+ 71 * 47 + a cc-op
  1 dst base cc-op ;
: cc-lut2 ( dst base a b -- ) L{ dst base a b }
  3 cc-room 1 cc-slot @ 2 + 71 * 47 + a cc-op
  1 cc-slot @ 1+ 71 * 48 + b cc-op 1 dst base cc-op ;
: cc-lut3 ( width dst base a b c stride -- ) L{ width dst base a b c stride }
  4 cc-room 1 cc-slot @ 3 + 71 * 47 + stride + a cc-op
  1 cc-slot @ 2 + 71 * 48 + stride + b cc-op
  1 cc-slot @ 1+ 71 * 49 + stride + c cc-op
  width dst base cc-op ;

variable cc-zero
variable cc-one
variable cc-add-entry
variable cc-sub-entry
variable cc-eq-entry
variable cc-lt-entry
variable cc-bool-entry
variable cc-output-entry
variable cc-library-layer
variable cc-library-constants
variable cc-library-end
: cc-full-add
  32 0 do
    2 cc-tmp cc-table-base cc-a i + cc-b i + cc-carry 1 cc-lut3
    1 cc-r i + cc-tmp cc-op 1 cc-carry cc-tmp 1+ cc-op
  loop cc-lret cc-dynamic ;
: cc-library
  cc-code-base cc-origin ! cc-data-base cc-emission-base ! cc-image cc-emission-buffer !
  0 cc-layer ! 3 cc-slot ! cc-constant-base cc-constants !
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
  cc-current cc-bool-entry ! 32 cc-r cc-zero @ cc-op
  32 0 do cc-r cc-table-base 24 + cc-r cc-a i + cc-lut2 loop
  cc-lret cc-dynamic
  cc-current cc-output-entry !
  32 0 do 1 cc-output i 8 / 8 * 7 + i 7 and - +
    cc-r i + cc-op loop
  cc-current cc-layer-bits + cc-jump
  32 cc-output 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-layer @ cc-library-layer ! cc-constants @ cc-library-constants !
  cc-current cc-library-end ! ;
cc-library

\ This small guard is installed before the large payload is read. Its code
\ is constant; only the expected count and success entry depend on the C.
2031616 constant cc-guard-data
2097152 constant cc-guard-code
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
  cc-code-base cc-origin ! cc-data-base cc-emission-base ! cc-image cc-emission-buffer !
  cc-library-layer @ cc-layer ! 3 cc-slot ! ;
cc-prepare-guard

: cc-invoke ( lhs rhs entry -- result ) L{ lhs rhs entry }
  3 cc-room 32 cc-a lhs cc-op 32 cc-b rhs cc-op
  cc-current cc-layer-bits + cc-const 24 cc-lret rot cc-op
  entry cc-jump cc-cell dup 32 swap cc-r cc-op ;
: cc-truth ( value -- result ) cc-zero @ cc-bool-entry @ cc-invoke ;
: cc-invert ( value -- result ) cc-cell L{ value result }
  32 result cc-zero @ cc-op
  result cc-table-base 40 + value cc-lut1 result ;
: cc-branch ( condition -- table ) L{ condition }
  cc-constants @ 63 + 63 invert and cc-constants !
  0 cc-const >r 0 cc-const drop
  3 cc-room 1 cc-slot @ 1+ 71 * 52 + condition cc-op
  24 cc-jaddr r@ cc-op cc-jaddr cc-dynamic r> ;

\ Lexer: names and numbers refer to source bytes, never to host parsing.
: cc-peek cc-pos @ cc-length @ < if cc-source cc-pos @ + c@ else -1 then ;
: cc-step 1 cc-pos +! ;
: cc-within ( n lo hi -- flag ) over - >r - r> u< ;
: cc-alpha ( c -- flag )
  dup 97 123 cc-within over 65 91 cc-within or swap 95 = or ;
: cc-digit ( c -- flag ) 48 58 cc-within ;
: cc-namechar dup cc-alpha swap cc-digit or ;
: cc-space dup 32 = swap 9 14 cc-within or ;
: cc-comment
  cc-step cc-step
  begin
    cc-peek -1 = if s" unfinished comment" cc-fail then
    cc-peek 42 = cc-pos @ 1+ cc-length @ < and if
      cc-source cc-pos @ 1+ + c@ 47 = else 0 then
    if cc-step cc-step exit then cc-step
  again ;
: cc-skip
  begin
    cc-peek cc-space if cc-step else
      cc-peek 47 = cc-pos @ 1+ cc-length @ < and if
        cc-source cc-pos @ 1+ + c@ dup 47 = if
          drop begin cc-peek dup -1 <> swap 10 <> and while cc-step repeat
        else 42 = if cc-comment
        else exit then then
      else exit then
    then
  again ;
: cc-text cc-source cc-token-start @ + cc-token-size @ ;
: cc-is ( addr len -- flag ) cc-text compare 0= ;
variable cc-radix
variable cc-number-start
: cc-number-next
  0 cc-number ! 10 cc-radix !
  cc-peek 48 = cc-pos @ 1+ cc-length @ < and if
    cc-source cc-pos @ 1+ + c@ dup 120 = swap 88 = or if
      cc-step cc-step 16 cc-radix !
    then
  then cc-pos @ cc-number-start !
  begin cc-peek dup cc-digit if 48 - else
    dup 97 103 cc-within if 87 - else
      dup 65 71 cc-within if 55 - else drop 99 then then then
    dup cc-radix @ <
  while
    cc-radix @ 10 = if
      cc-number @ 429496729 u> cc-number @ 429496729 = 2 pick 5 > and or
    else cc-number @ 268435455 u> then
    if drop s" integer literal out of range" cc-fail then
    cc-number @ cc-radix @ * + cc-number ! cc-step
  repeat drop
  cc-pos @ cc-number-start @ = if s" malformed number" cc-fail then
  1 cc-token ! ;
: cc-next
  cc-skip cc-pos @ cc-token-start ! 0 cc-token-size !
  cc-peek dup -1 = if drop 0 cc-token ! exit then
  dup 0= if s" NUL in source" cc-fail then
  dup cc-alpha if drop
    begin cc-peek cc-namechar while cc-step repeat 2 cc-token !
  else dup cc-digit if drop cc-number-next
  else cc-step cc-token !
    cc-token @ dup 61 = over 33 = or over 60 = or swap 62 = or
    cc-peek 61 = and if
      cc-token @ dup 61 = if drop 256 else dup 33 = if drop 257 else
        60 = if 258 else 259 then then then cc-token ! cc-step
    then
  then then cc-pos @ cc-token-start @ - cc-token-size ! ;
: cc-expect ( token -- ) cc-token @ <> if s" unexpected token" cc-fail then cc-next ;

create cc-function-names 16 32 * allot
create cc-function-entry 16 cells allot
create cc-function-return 16 cells allot
create cc-function-value 16 cells allot
create cc-function-argc 16 cells allot
create cc-function-params 16 8 * cells allot
create cc-symbol-names 128 32 * allot
create cc-symbol-address 128 cells allot
variable cc-function-count
variable cc-function-index
variable cc-symbol-count
variable cc-main-index
variable cc-depth
: cc-find ( names count -- index ) L{ names entries }
  entries 0 ?do cc-text names i 32 * + count compare 0= if i unloop exit then
  loop -1 ;
: cc-find-symbol cc-symbol-names cc-symbol-count @ cc-find ;
: cc-find-function cc-function-names cc-function-count @ cc-find ;
: cc-name! ( destination -- )
  s" int" cc-is s" void" cc-is or s" if" cc-is or s" else" cc-is or
  s" while" cc-is or s" return" cc-is or if s" reserved name" cc-fail then
  cc-token @ 2 <> cc-token-size @ 31 > or cc-limit cc-text rot place ;
: cc-symbol ( -- target )
  cc-find-symbol -1 <> if s" duplicate local name" cc-fail then
  cc-symbol-count @ 128 >= cc-limit
  cc-symbol-names cc-symbol-count @ 32 * + cc-name!
  cc-cell dup cc-symbol-address cc-symbol-count @ cells + !
  1 cc-symbol-count +! ;
: cc-fget ( index array -- value ) swap cells + @ ;
: cc-fset ( value index array -- ) swap cells + ! ;
: cc-param ( fn index -- target ) swap 8 * + cells cc-function-params + @ ;
: cc-nest 1 cc-depth +! cc-depth @ 32 > cc-limit ;
: cc-unnest -1 cc-depth +! ;
defer cc-expression
defer cc-statement

: cc-call ( fn -- value ) 0 L{ fn nargs }
  fn 0< fn cc-function-index @ >= or if s" unknown or recursive function" cc-fail then
  fn cc-main-index @ = if s" main cannot be called" cc-fail then
  40 cc-expect
  cc-token @ 41 <> if
    begin nargs 8 >= cc-limit cc-expression
      nargs 1+ 2 (local!)
      cc-token @ 44 = if cc-next 0 else -1 then
    until
  then
  41 cc-expect
  nargs fn cc-function-argc cc-fget <> if s" wrong argument count" cc-fail then
  nargs 0 ?do 32 fn nargs 1- i - cc-param rot cc-op loop
  1 cc-room cc-current cc-layer-bits + cc-const
  24 fn cc-function-return cc-fget rot cc-op
  fn cc-function-entry cc-fget cc-jump
  cc-cell dup 32 swap fn cc-function-value cc-fget cc-op ;

: cc-primary ( -- target )
  cc-token @ 40 = if cc-next cc-nest cc-expression cc-unnest 41 cc-expect exit then
  cc-token @ 1 = if cc-number @ cc-const cc-next exit then
  cc-token @ 2 = if
    cc-find-symbol >r cc-find-function >r cc-next
    cc-token @ 40 = if r> r> drop cc-nest cc-call cc-unnest else
      r> drop r> dup 0< if drop s" unknown variable" cc-fail then
      cells cc-symbol-address + @ then exit
  then s" expected expression" cc-fail ;
: cc-unary ( -- target )
  cc-token @ 45 = if cc-next cc-nest recurse cc-unnest
    cc-zero @ swap cc-sub-entry @ cc-invoke exit then
  cc-token @ 33 = if cc-next cc-nest recurse cc-unnest
    cc-truth cc-invert exit then cc-primary ;
: cc-additive ( -- target )
  cc-unary begin cc-token @ dup 43 = swap 45 = or while
    cc-token @ >r cc-next cc-unary r> 43 = if cc-add-entry @ else cc-sub-entry @ then
    cc-invoke repeat ;
: cc-relational-op ( lhs rhs op -- target ) L{ lhs rhs op }
  op 60 = if lhs rhs cc-lt-entry @ cc-invoke exit then
  op 62 = if rhs lhs cc-lt-entry @ cc-invoke exit then
  op 258 = if rhs lhs cc-lt-entry @ cc-invoke cc-invert else
    lhs rhs cc-lt-entry @ cc-invoke cc-invert then ;
: cc-relational ( -- target )
  cc-additive begin cc-token @ dup 60 = over 62 = or over 258 = or swap 259 = or while
    cc-token @ >r cc-next cc-additive r> cc-relational-op repeat ;
: cc-equality ( -- target )
  cc-relational begin cc-token @ dup 256 = swap 257 = or while
    cc-token @ >r cc-next cc-relational cc-eq-entry @ cc-invoke
    r> 257 = if cc-invert then repeat ;
' cc-equality is cc-expression

: cc-return-value ( value -- )
  cc-function-index @ cc-main-index @ = if 32 cc-r rot cc-op cc-output-entry @ cc-jump else
    32 cc-function-index @ cc-function-value cc-fget rot cc-op
    cc-function-index @ cc-function-return cc-fget cc-dynamic then ;
: cc-forward ( -- field )
  cc-current 18152 + >r 0 cc-jump r> ;
: cc-link! ( field target -- ) swap 24 swap cc-value! ;
: cc-if
  cc-next 40 cc-expect cc-expression 41 cc-expect cc-truth cc-branch L{ table }
  table 32 + cc-current cc-patch cc-nest cc-statement cc-unnest
  s" else" cc-is if
    cc-forward >r table cc-current cc-patch cc-next
    cc-nest cc-statement cc-unnest r> cc-boundary cc-link!
  else table cc-boundary cc-patch then ;
: cc-while
  cc-next cc-boundary 0 L{ head table }
  40 cc-expect cc-expression 41 cc-expect cc-truth cc-branch 2 (local!)
  table 32 + cc-current cc-patch cc-nest cc-statement cc-unnest
  head cc-jump table cc-current cc-patch ;
: cc-declaration
  cc-next cc-symbol >r cc-next
  cc-token @ 61 = if cc-next cc-expression else cc-zero @ then
  32 r> rot cc-op 59 cc-expect ;
: cc-assignment-or-call
  cc-token-start @ cc-find-symbol L{ start symbol }
  cc-next cc-token @ 61 = if
    symbol 0< if s" unknown assignment target" cc-fail then
    cc-next cc-expression 32 symbol cells cc-symbol-address + @ rot cc-op
  else start cc-pos ! cc-next cc-expression drop then 59 cc-expect ;
: cc-statement-body
  cc-token @ 123 = if
    cc-symbol-count @ >r cc-next begin cc-token @ 125 <> while
      cc-token @ 0= if s" unfinished block" cc-fail then
      cc-nest cc-statement cc-unnest
    repeat cc-next r> cc-symbol-count ! exit then
  s" int" cc-is if cc-declaration exit then
  s" if" cc-is if cc-if exit then
  s" while" cc-is if cc-while exit then
  s" return" cc-is if cc-next cc-expression 59 cc-expect cc-return-value exit then
  cc-token @ 59 = if cc-next exit then
  cc-token @ 2 = if cc-assignment-or-call exit then
  s" unsupported statement" cc-fail ;
' cc-statement-body is cc-statement

: cc-function
  s" int" cc-is 0= if s" expected int function" cc-fail then cc-next
  cc-find-function -1 <> if s" duplicate function" cc-fail then
  cc-function-count @ dup cc-function-index ! 16 >= cc-limit
  cc-function-names cc-function-index @ 32 * + cc-name!
  s" main" cc-is if cc-function-index @ cc-main-index ! then
  cc-boundary cc-function-index @ cc-function-entry cc-fset
  cc-cell cc-function-index @ cc-function-return cc-fset
  cc-cell cc-function-index @ cc-function-value cc-fset
  0 cc-function-index @ cc-function-argc cc-fset
  1 cc-function-count +! 0 cc-symbol-count ! cc-next 40 cc-expect
  cc-token @ 41 <> if
    s" void" cc-is if cc-next else
      begin
        s" int" cc-is 0= if s" expected int parameter" cc-fail then cc-next
        cc-function-index @ cc-function-argc cc-fget dup 8 >= cc-limit >r
        cc-symbol cc-function-index @ 8 * r@ + cells cc-function-params + !
        r> 1+ cc-function-index @ cc-function-argc cc-fset cc-next
        cc-token @ 44 = if cc-next 0 else -1 then
      until
    then
  then 41 cc-expect
  cc-function-index @ cc-main-index @ = if
    cc-function-index @ cc-function-argc cc-fget 0<> if s" main takes no parameters" cc-fail then
  then
  cc-token @ 123 <> if s" expected function body" cc-fail then
  cc-statement cc-zero @ cc-return-value ;

: cc-finish
  cc-main-index @ 0< if s" main missing" cc-fail then
  cc-main-index @ cc-function-entry cc-fget 32 64 cc-guard-constants cc-bits!
  cc-current cc-data-base - 2 * 32 0 cc-guard-constants cc-bits! ;
: cc-export
  cc-prelude cc-prelude-bytes @ dup >r cs-write r> <> if 1 cs-exit then
  cc-guard-data cc-guard-constants 36 cc-install
  cc-record 37 0 fill
  24 cc-load-status 118 0 cc-record cc-row-at
  cc-current cc-data-base - cc-data-base 0 71 cc-record cc-row-at
  cc-layer-bits 0 cc-guard-code 213 cc-record cc-row-at
  cc-record 37 cs-write 37 <> if 1 cs-exit then
  cc-image cc-current cc-data-base - 8 / dup >r cs-write r> <> if 1 cs-exit then ;
: cc-read-source
  0 cc-length !
  begin cc-source cc-length @ + cc-source-max 1+ cc-length @ - cs-read
    dup 0< if drop s" input error" cc-fail then
    dup 0= if drop exit then cc-length +!
    cc-length @ cc-source-max > cc-limit
  again ;
: CC-RUN
  0 cc-pos ! 0 cc-token-start ! 0 cc-depth ! 0 cc-function-count !
  -1 cc-main-index ! cc-data-base cc-data !
  cc-code-base cc-origin ! cc-data-base cc-emission-base ! cc-image cc-emission-buffer !
  cc-library-layer @ cc-layer ! 3 cc-slot !
  cc-library-constants @ cc-constants !
  cc-read-source cc-next begin cc-token @ while cc-function repeat
  cc-finish cc-export 0 cs-exit ;
