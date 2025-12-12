#!/bin/sh

set -e

die() { echo "Ошибка: $1" >&2; exit "$2"; }

[ "$#" -eq 1 ] && [ -f "$1" ] || die "Укажите один существующий исходный файл" 2

TEMP_DIR=$(mktemp -d build.XXXXXX) || die "Не удалось создать временный каталог" 3
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT QUIT TERM

cp "$1" "$TEMP_DIR/$(basename "$1")" || die "Не удалось скопировать файл во временный каталог" 4

OUTPUT_FILENAME=$(grep '&Output:' "$1" | sed 's/.*&Output:[[:space:]]*\([^[:space:]]*\).*/\1/' | head -n 1) || die "Комментарий '&Output:' не найден в '$1'" 5

case "$1" in
    *.c)    gcc -Wall -o "$TEMP_DIR/$OUTPUT_FILENAME" "$TEMP_DIR/$(basename "$1")" || die "Сборка файла C не удалась" 10 ;;
    *.cpp)  g++ -Wall -o "$TEMP_DIR/$OUTPUT_FILENAME" "$TEMP_DIR/$(basename "$1")" || die "Сборка файла C++ не удалась" 11 ;;
    *.tex)  pdflatex -interaction=nonstopmode -jobname="$TEMP_DIR/$(basename "$OUTPUT_FILENAME" .pdf)" "$TEMP_DIR/$(basename "$1")" >/dev/null && \
            pdflatex -interaction=nonstopmode -jobname="$TEMP_DIR/$(basename "$OUTPUT_FILENAME" .pdf)" "$TEMP_DIR/$(basename "$1")" >/dev/null || die "Сборка файла TeX не удалась" 12 ;;
    *) die "Неподдерживаемый тип файла: '$1'." 6 ;;
esac

mv "$TEMP_DIR/$OUTPUT_FILENAME" "$OUTPUT_FILENAME"