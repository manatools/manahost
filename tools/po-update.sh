#!/bin/sh

set -e

if test "$1" = "-h" -o "$1" = "--help"; then
	echo "Use: $0 [<language>]"
	echo "Run without arguments to update all translation files."
	exit 0
fi

cd "$(readlink -f "$(dirname "$0")/..")"

VERSION="0.1.0"
DOMAIN="manahost"

POT_DIR="$PWD/po"
test -d "$POT_DIR"

POT_FILE="$POT_DIR/$DOMAIN.pot"
PY_SOURCES="$(find manahost -type f -name '*.py' | sort)"
DESKTOP_FILE="share/applications/.org.mageia.manahost.desktop"

if test -z "$PY_SOURCES"; then
	echo "No Python sources found under manahost/"
	exit 1
fi

/usr/bin/xgettext \
	--package-name "$DOMAIN" \
	--package-version "$VERSION" \
	--language=Python --from-code=UTF-8 --keyword=_ --keyword=N_ \
	--no-escape --add-location --sort-by-file \
	--add-comments=I18N \
	--output="$POT_FILE" \
	$PY_SOURCES

if test -f "$DESKTOP_FILE"; then
	/usr/bin/xgettext \
		--join-existing \
		--package-name "$DOMAIN" \
		--package-version "$VERSION" \
		--language=Desktop --from-code=UTF-8 \
		--keyword=Name --keyword=Comment \
		--no-escape --add-location --sort-by-file \
		--output="$POT_FILE" \
		"$DESKTOP_FILE"
fi

/bin/sed --in-place --expression="s/charset=CHARSET/charset=UTF-8/" "$POT_FILE"
/bin/sed --in-place --expression="s|$PWD/||g" "$POT_FILE"

update_po() {
	local LL_CC="$1"
	local PO_FILE="$POT_DIR/$LL_CC.po"

        echo "Update $(basename "$PO_FILE"):"
	/usr/bin/msgmerge \
		--update --no-fuzzy-matching \
		--no-escape --add-location --sort-by-file \
		--lang="$LL_CC" \
		"$PO_FILE" "$POT_FILE"
}

if test "$1"; then
	update_po "$1"
else
	found_po=0
	for po_file in "$POT_DIR"/*.po; do
		test -e "$po_file" || continue
		found_po=1
		po_basename="$(basename "$po_file")"
		update_po "${po_basename%.po}"
	done
	if test "$found_po" -eq 0; then
		echo "No .po files found in $POT_DIR, template generated only: $POT_FILE"
	fi
fi
