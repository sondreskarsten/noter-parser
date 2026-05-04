"""Per-table extractors. Each module exposes `build(data, orgnr, year)` returning
a list of dict rows (possibly empty) for that table for that (orgnr, year)."""

from . import (
    documents,
    aksjekapital_struktur,
    aksjonaerer,
    egenkapital_summary,
    lonn_ytelser,
    godtgjorelse_ledende,
    revisor_honorar,
    bankinnskudd_bundne,
    skatt_aaret,
    anleggsmidler_rollforward,
    relatert_part_kreditt,
    skattefunn,
    kontingente_forpliktelser,
    going_concern,
)

REGISTRY = {
    "documents": documents.build,
    "aksjekapital_struktur": aksjekapital_struktur.build,
    "aksjonaerer": aksjonaerer.build,
    "egenkapital_summary": egenkapital_summary.build,
    "lonn_ytelser": lonn_ytelser.build,
    "godtgjorelse_ledende": godtgjorelse_ledende.build,
    "revisor_honorar": revisor_honorar.build,
    "bankinnskudd_bundne": bankinnskudd_bundne.build,
    "skatt_aaret": skatt_aaret.build,
    "anleggsmidler_rollforward": anleggsmidler_rollforward.build,
    "relatert_part_kreditt": relatert_part_kreditt.build,
    "skattefunn": skattefunn.build,
    "kontingente_forpliktelser": kontingente_forpliktelser.build,
    "going_concern": going_concern.build,
}
