#!/bin/bash

OUTPUT="merged_output.txt"

> "$OUTPUT"

find . -type f -not -path "./$OUTPUT" -exec cat {} \; >> "$OUTPUT"

echo "Готово! Все файлы объединены в $OUTPUT"
