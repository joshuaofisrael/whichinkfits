"""Canon, Epson, and Brother records taken from the manufacturers' own pages.

Retrieved 16 Nov 2026. Each supply row is a number that page actually prints.
Ink volume is not a page yield, so volume stays in the note and the yield cell
stays empty unless that same page prints a page yield.
"""

VERIFIED = "2026-11-16"

def S(sku, color, capacity="standard", yield_text="", family="", note=""):
    return {"sku": sku, "color": color, "capacity": capacity, "yield_text": yield_text, "family": family, "note": note}

def P(brand, name, slug, series, series_name, medium, supplies, sources, notes=None):
    return {
        "brand": brand, "name": name, "slug": slug, "series": series, "series_name": series_name,
        "medium": medium, "groups": [{"label": "", "supplies": supplies, "regions": []}],
        "sources": sources, "notes": notes or [], "verified": VERIFIED,
    }

PG245_PAGE = ("Canon PG-245 / CL-246 value pack", "https://www.usa.canon.com/shop/p/pg-245-cl-246-value-pack")
MG_ARTICLE = ("What inks are compatible with the printer? (MG2420 / MG2500 Series / MG2900 Series), Canon Knowledge Base", "https://support.usa.canon.com/kb/s/article/ART165647")
PG275_PAGE = ("Canon PG-275 / CL-276 value pack", "https://www.usa.canon.com/shop/p/pg-275-cl-276-value-pack")
PG275XL_PAGE = ("Canon PG-275 XL / CL-276 XL value pack", "https://www.usa.canon.com/shop/p/pg-275-xl-cl-276-xl-value-pack")
TR4720_INK = ("Replacing an ink cartridge, PIXMA TR4720 / TR4722, Canon Knowledge Base", "https://support.usa.canon.com/kb/s/article/ART180252")
TR4720_SHOP = ("Canon PIXMA TR4720", "https://www.usa.canon.com/shop/p/pixma-tr4720")
PG260_ARTICLE = ("Replacing an ink cartridge, PIXMA TR7020 / TR7020a / TR7022 / TR7022a, Canon Knowledge Base", "https://support.usa.canon.com/kb/s/article/ART177695")
TS5320 = ("Canon Support for PIXMA TS5320", "https://www.usa.canon.com/support/p/pixma-ts5320")
TS6420A = ("Canon PIXMA TS6420a", "https://www.usa.canon.com/shop/p/pixma-ts6420a")
PG260_PACK = ("Canon PG-260 / CL-261 value pack", "https://www.usa.canon.com/shop/p/pg-260-cli-261-value-pack")
GI_TYPES = ("Ink types for MegaTank inkjet printers, Canon Knowledge Base", "https://support.usa.canon.com/kb/s/article/ART180810")
GI_LIST = ("Ink bottles for PIXMA G Series and MAXIFY GX Series, Canon Knowledge Base", "https://support.usa.canon.com/kb/s/article/ART180888")
G3270_SHOP = ("Canon MegaTank PIXMA G3270", "https://www.usa.canon.com/shop/p/pixma-g3270")
G3270_REFILL = ("Refill the ink tanks, PIXMA G3270 / PIXMA G3272, Canon Knowledge Base", "https://support.usa.canon.com/kb/s/article/ART180951")

STD245 = [S("PG-245", "Black", family="canon-pg-245-cl-246"), S("CL-246", "Color", family="canon-pg-245-cl-246")]
FULL245 = STD245 + [
    S("PG-245XL", "Black", "high yield", family="canon-pg-245-cl-246"),
    S("CL-246XL", "Color", "high yield", family="canon-pg-245-cl-246"),
    S("PG-243", "Black", family="canon-pg-243-cl-244", note="Canon calls PG-243 and CL-244 economy inks on the MG series article."),
    S("CL-244", "Color", family="canon-pg-243-cl-244", note="Canon calls PG-243 and CL-244 economy inks on the MG series article."),
]
PG275 = [
    S("PG-275", "Black", family="canon-pg-275-cl-276"),
    S("PG-275XL", "Black", "high yield", family="canon-pg-275-cl-276"),
    S("CL-276", "Color", family="canon-pg-275-cl-276"),
    S("CL-276XL", "Color", "high yield", family="canon-pg-275-cl-276"),
]
PG260 = [
    S("PG-260", "Black", family="canon-pg-260-cl-261"),
    S("PG-260XL", "Black", "high yield", family="canon-pg-260-cl-261"),
    S("CL-261", "Color", family="canon-pg-260-cl-261"),
    S("CL-261XL", "Color", "high yield", family="canon-pg-260-cl-261"),
]

def gi(num, family):
    return [
        S(num, "Black", family=family, note="Pigment black bottle."),
        S(num, "Cyan", family=family, note="Dye color bottle."),
        S(num, "Magenta", family=family, note="Dye color bottle."),
        S(num, "Yellow", family=family, note="Dye color bottle."),
    ]

def canon():
    out = []
    vol245 = "The MG series article prints ink volume, not a page yield: PG-243 5.6 ml, CL-244 6.2 ml, PG-245 8.0 ml, CL-246 9.0 ml, PG-245XL 12.0 ml, CL-246XL 13.0 ml."
    for code in ["iP2820", "MX492", "MG3020", "MG2525", "TS3120", "TS302", "TS202", "TR4520", "TS3320"]:
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "pg-245-cl-246", "Canon PG-245 and CL-246 printers",
                     "ink cartridges", STD245, [PG245_PAGE],
                     ["Canon prints this model as " + code + " on the PG-245 / CL-246 value pack. That page does not list an XL or a PG-243 cartridge for it."]))
    for code, sources, supplies, notes in [
        ("MG2420", [PG245_PAGE, MG_ARTICLE], FULL245, [vol245, "The value pack lists MG2420. The MG series article also lists PG-243, CL-244, and the XL sizes for PIXMA MG2420."]),
        ("MG2920", [PG245_PAGE, MG_ARTICLE], FULL245, [vol245, "The value pack lists MG2920. The MG series article also lists PG-243, CL-244, and the XL sizes for PIXMA MG2920."]),
        ("MG2924", [PG245_PAGE, MG_ARTICLE], FULL245, [vol245, "The value pack lists MG2924. The MG series article also lists PG-243, CL-244, and the XL sizes for PIXMA MG2924."]),
        ("MG2520", [MG_ARTICLE], FULL245, [vol245, "The MG series article names PIXMA MG2520. The value pack list we checked does not."]),
        ("MG2922", [MG_ARTICLE], FULL245, [vol245, "The MG series article names PIXMA MG2922. The value pack list we checked does not."]),
    ]:
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "pg-245-cl-246", "Canon PG-245 and CL-246 printers",
                     "ink cartridges", supplies, sources, notes))
    mix = "Canon's TR4720 / TR4722 replacement article says you can use both a standard cartridge and an XL cartridge in the printer, for example PG-275 and CL-276XL."
    vol275 = "Canon prints ink volume, not a page yield: standard PG-275 5.6 ml and CL-276 6.2 ml; XL PG-275 11.9 ml and CL-276 12.6 ml."
    for code in ["TS3520", "TS3522", "TS3720", "TS3722", "TR4720", "TR4722"]:
        src = [PG275_PAGE, PG275XL_PAGE]
        notes = [vol275]
        if code in ("TR4720", "TR4722"):
            src = [TR4720_INK, TR4720_SHOP, PG275_PAGE, PG275XL_PAGE]
            notes.append(mix)
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "pg-275-cl-276", "Canon PG-275 and CL-276 printers",
                     "ink cartridges", PG275, src, notes))
    vol260 = "Canon prints ink volume, not a page yield, on the TS5320 and TR7020a pages: PG-260 7.5 ml standard and 14.3 ml XL; CL-261 8.3 ml standard and 12.2 ml XL."
    for code, src in [
        ("TR7020", [PG260_ARTICLE, PG260_PACK]),
        ("TR7020a", [PG260_ARTICLE]),
        ("TR7022", [PG260_ARTICLE]),
        ("TR7022a", [PG260_ARTICLE]),
        ("TS5320", [TS5320, PG260_PACK]),
        ("TS6420a", [TS6420A]),
    ]:
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "pg-260-cl-261", "Canon PG-260 and CL-261 printers",
                     "ink cartridges", PG260, src, [vol260]))
    gi21_note = "Canon prints bottle volume, not a per bottle page yield: GI-21 black 135.0 ml pigment, and cyan, magenta, and yellow 70.0 ml dye each."
    for code in ["G1220", "G1230", "G2260", "G2270", "G3260", "G3270", "G3290", "G4270", "G4280"]:
        src = [GI_TYPES, GI_LIST]
        notes = [gi21_note]
        if code == "G3270":
            src = [G3270_SHOP, G3270_REFILL, GI_TYPES, GI_LIST]
            notes.append("Canon's G3270 shop page prints a full bottle set yield in default mode: up to 6,000 black and white pages and up to 7,700 color pages. That figure is for the set, not for one bottle. The refill article also names G3272 for the same GI-21 bottles. G3272 does not have its own page here.")
        elif code in ("G1230", "G2270"):
            notes.append("Named on Canon's ink bottle article. The ink types table we checked does not repeat this code.")
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "gi-21", "Canon GI-21 MegaTank printers",
                     "ink bottles", gi("GI-21", "canon-gi-21"), src, notes))
    gi20_note = "Canon prints bottle volume, not a per bottle page yield: GI-20 black 170.0 ml pigment, and cyan, magenta, and yellow 70.0 ml dye each."
    for code in ["G5020", "G6020", "G7020"]:
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "gi-20", "Canon GI-20 MegaTank printers",
                     "ink bottles", gi("GI-20", "canon-gi-20"), [GI_TYPES], [gi20_note]))
    gi290_note = "Canon prints bottle volume, not a per bottle page yield: GI-290 black 135.0 ml pigment, and cyan, magenta, and yellow 70.0 ml dye each."
    for code in ["G1200", "G2200", "G3200", "G4200", "G4210"]:
        out.append(P("canon", "Canon PIXMA " + code, "pixma-" + code.lower(), "gi-290", "Canon GI-290 MegaTank printers",
                     "ink bottles", gi("GI-290", "canon-gi-290"), [GI_TYPES], [gi290_note]))
    return out

EPSON_212 = ("Epson 212 ink", "https://epson.com/For-Home/Ink/Epson%26reg%3B-212%26reg%3B-Ink/i/T212")
EPSON_PARTS = ("Ink cartridge and maintenance box part numbers, Epson support (XP-4100, XP-4105, WF-2830, WF-2850)", "https://files.support.epson.com/docid/cpd5/cpd56917/source/printers/source/ink_functions/reference/ink_part_numbers_us_canada_xp4100_4105_wf2830_2850.html")
XP4105 = ("Epson Expression Home XP-4105", "https://epson.com/For-Home/Printers/Inkjet/Expression-Home-XP-4105-Small-in-One-Printer/p/C11CG33202")
WF2830 = ("Which ink cartridges should I use with this product? Epson WorkForce WF-2830", "https://epson.com/faq/SPT_C11CG30201~faq-000060e-wf2830")
ET2800 = ("Which Epson ink bottles should I use with this product? Epson ET-2800", "https://epson.com/faq/SPT_C11CJ66202~faq-00007ec-et2800_2803")
EPSON_522 = ("Epson EcoTank ET-2800 ink finder", "https://epson.com/InkFinder/i/C11CJ66201")

def epson():
    y212 = "Epson's XP-4105 page prints ISO replacement yields for these cartridge numbers: 212 black 150 pages and 212 color 130 pages; 212XL black 500 pages and 212XL color 350 pages. The yield is for the cartridge. Epson's part number page groups XP-4100, XP-4105, WF-2830, and WF-2850 on one table."
    colors = ["Black", "Cyan", "Magenta", "Yellow"]
    supplies = []
    for color in colors:
        yb = "150 ISO pages" if color == "Black" else "130 ISO pages"
        yx = "500 ISO pages" if color == "Black" else "350 ISO pages"
        supplies.append(S("212", color, yield_text=yb, family="epson-212"))
        supplies.append(S("212XL", color, "high yield", yield_text=yx, family="epson-212"))
    supplies.append(S("C9344", "Maintenance box", family="epson-c9344", note="Epson lists this maintenance box part number beside the 212 cartridges. It is not ink."))
    out = []
    specs = [
        ("Epson WorkForce WF-2830", "wf-2830", [EPSON_212, EPSON_PARTS, WF2830, XP4105]),
        ("Epson WorkForce WF-2850", "wf-2850", [EPSON_212, EPSON_PARTS, XP4105]),
        ("Epson Expression Home XP-4100", "xp-4100", [EPSON_212, EPSON_PARTS, XP4105]),
        ("Epson Expression Home XP-4105", "xp-4105", [EPSON_212, EPSON_PARTS, XP4105]),
    ]
    for name, slug, src in specs:
        out.append(P("epson", name, slug, "212", "Epson 212 ink printers", "ink cartridges", supplies, src, [y212]))
    bottles = [
        S("522120", "Black", family="epson-522"),
        S("522220", "Yellow", family="epson-522"),
        S("522320", "Magenta", family="epson-522"),
        S("522420", "Cyan", family="epson-522"),
    ]
    out.append(P("epson", "Epson EcoTank ET-2800", "et-2800", "522", "Epson 522 ink bottle printers", "ink bottles", bottles, [ET2800, EPSON_522],
                 ["These are ink bottles, not cartridges. Epson's ET-2800 FAQ prints part numbers 522120 black, 522220 yellow, 522320 magenta, and 522420 cyan. That FAQ does not print a page yield."]))
    return out

TN760 = ("Brother TN760 high yield toner", "https://www.brother-usa.com/p/ink-toner/TN760")
DR_BUND = ("Brother DR730 and TN760 bundle", "https://www.brother-usa.com/p/ink-toner/DR730TN760BUND")
LC406_4 = ("Brother LC406 4 pack", "https://www.brother-usa.com/p/ink-toner/LC4064PKS")
LC406C = ("Brother LC406 cyan cartridge", "https://www.brother-usa.com/p/ink-toner/LC406CS")
J4335 = ("Brother MFC-J4335DW", "https://www.brother-usa.com/p/inkjet-printers/MFCJ4335DW")

def brother():
    toner_models = ["DCP-L2550DW", "HL-L2350DW", "HL-L2370DW", "HL-L2370DW XL", "HL-L2390DW", "HL-L2395DW", "MFC-L2710DW", "MFC-L2750DW", "MFC-L2750DW XL", "MFC-L2690DW", "MFC-L2730DW", "MFC-L2717DW"]
    drum_models = ["DCP-L2550DW", "HL-L2350DW", "HL-L2370DW", "HL-L2370DW XL", "HL-L2390DW", "HL-L2395DW", "MFC-L2710DW", "MFC-L2750DW", "MFC-L2750DW XL"]
    ink_models = ["MFC-J4335DW", "MFC-J4345DW XL", "MFC-J4535DW", "MFC-J5855DW", "MFC-J5955DW", "MFC-J6555DW", "MFC-J6955DW"]
    out = []
    for code in toner_models:
        supplies = [S("TN-760", "Black", "high yield", "About 3,000 pages", "brother-tn-760", "Brother says approximate page yield in accordance with ISO/IEC 19752 (letter/A4).")]
        src = [TN760]
        notes = ["Brother's TN760 page calls this a high yield black toner and lists this model under developed for Brother printers."]
        if code in drum_models:
            supplies.append(S("DR-730", "Drum", family="brother-dr-730", note="The bundle page says the drum is a 12,000 page drum and that drum yield is approximate and may vary by type of use."))
            src.append(DR_BUND)
            notes.append("The drum is listed because the DR730 and TN760 bundle page names this model. Brother does not describe the drum as toner.")
        else:
            notes.append("The TN760 page names this model. The DR730 bundle page we checked does not, so no drum is listed here.")
        slug = code.lower().replace(" ", "-")
        out.append(P("brother", "Brother " + code, slug, "tn-760", "Brother TN-760 printers", "toner", supplies, src, notes))
    ink = []
    for color, y, yx in [("Black", "3,000 pages", "6,000 pages"), ("Cyan", "1,500 pages", "5,000 pages"), ("Magenta", "1,500 pages", "5,000 pages"), ("Yellow", "1,500 pages", "5,000 pages")]:
        ink.append(S("LC406" + ("" if color != "Black" else ""), color, yield_text=y, family="brother-lc406"))
        ink.append(S("LC406XL", color, "high yield", yield_text=yx, family="brother-lc406"))
    # Black SKUs are LC406BK and LC406XLBK on Brother's yield footnote. Color pages say LC406C and so on.
    ink = [
        S("LC406BK", "Black", yield_text="3,000 pages", family="brother-lc406"),
        S("LC406XLBK", "Black", "high yield", yield_text="6,000 pages", family="brother-lc406"),
        S("LC406C", "Cyan", yield_text="1,500 pages", family="brother-lc406"),
        S("LC406XLC", "Cyan", "high yield", yield_text="5,000 pages", family="brother-lc406"),
        S("LC406M", "Magenta", yield_text="1,500 pages", family="brother-lc406"),
        S("LC406XLM", "Magenta", "high yield", yield_text="5,000 pages", family="brother-lc406"),
        S("LC406Y", "Yellow", yield_text="1,500 pages", family="brother-lc406"),
        S("LC406XLY", "Yellow", "high yield", yield_text="5,000 pages", family="brother-lc406"),
    ]
    ynote = "Brother's MFC-J4335DW page says replacement yields are approximate and calculated to ISO/IEC 24711: LC406BK 3,000 pages, LC406 cyan, magenta, and yellow 1,500 pages each, LC406XLBK 6,000 pages, and LC406XL cyan, magenta, and yellow 5,000 pages each. The LC406 4 pack and LC406 cyan pages list the same printer models."
    for code in ink_models:
        slug = code.lower().replace(" ", "-")
        out.append(P("brother", "Brother " + code, slug, "lc406", "Brother LC406 printers", "ink cartridges", ink, [J4335, LC406_4, LC406C], [ynote]))
    return out

def printers():
    return canon() + epson() + brother()
