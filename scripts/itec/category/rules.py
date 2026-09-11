# -*- coding: utf-8 -*-
"""กฎจัดหมวดสินค้า แปลงตรงจาก CASE WHEN ใน ci_item_category.sql

ลำดับในลิสต์ = ลำดับ WHEN ตัวแรกที่ตรงชนะ ห้ามสลับ
เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Item Category Mapping (SQL to Python).md
"""


def _f(d, name):
    """อ่าน flag แบบไม่สนตัวพิมพ์ · SQL เดิมเขียน IS_stand กับ IS_Stand ปนกัน"""
    return d[next(c for c in d.columns if c.lower() == name.lower())].astype(bool)


# ---------------------------------------------------------------- Main --
def _pc(d, fix):
    core = _f(d, "IS_iMac") | _f(d, "IS_PC") | _f(d, "IS_Desktop") | _f(d, "IS_Computer")
    nb = _f(d, "IS_Notebook") | _f(d, "IS_Macbook")
    # ของเดิมเป็น OR ซึ่งเกือบจริงเสมอ ตัวกรองจึงแทบไม่ทำงาน
    guard = ~nb if fix else (~_f(d, "IS_Notebook") | ~_f(d, "IS_Macbook"))
    return core & guard


def _notebook(d, fix):
    nb = _f(d, "IS_Notebook") | _f(d, "IS_Macbook")
    if fix:
        return nb
    core_not = (~_f(d, "IS_iMac") | ~_f(d, "IS_PC")
                | ~_f(d, "IS_Desktop") | ~_f(d, "IS_Computer"))
    return core_not & nb


def main_rules(fix_pc_notebook=False):
    return [
        ("Smart Phone", lambda d: _f(d, "IS_Smartphone") | _f(d, "IS_Mobile")
                                  | _f(d, "IS_Galaxy") | _f(d, "IS_iPhone")),
        ("Tablet", lambda d: _f(d, "IS_iPad") | _f(d, "IS_Tablet")),
        ("Smart Watch", lambda d: _f(d, "IS_Watch")),
        ("HeadSet&Earpiece", lambda d: _f(d, "IS_AirPod") | _f(d, "IS_HeadSet")
                                       | _f(d, "IS_HeadPhone")),
        ("Mouse&Keyboard", lambda d: _f(d, "IS_Mouse") | _f(d, "IS_Keyboard")),
        ("Software", lambda d: _f(d, "IS_Software")),
        ("Insurance", lambda d: _f(d, "IS_AppleCare") | _f(d, "IS_Insurance")
                                | _f(d, "IS_Care")),
        ("Console Gaming", lambda d: _f(d, "IS_Nintendo_SwitchG")
                                     | _f(d, "IS_NintendoSwitch") | _f(d, "IS_Playstation")),
        ("PC", lambda d: _pc(d, fix_pc_notebook)),
        ("Notebook", lambda d: _notebook(d, fix_pc_notebook)),
        ("PC&Notebook Component", lambda d: _f(d, "IS_GraphicCard") | _f(d, "IS_PowerSupply")
                                            | _f(d, "IS_Mainboard") | _f(d, "IS_RAM")
                                            | _f(d, "IS_CPU") | _f(d, "IS_Cooling")
                                            | _f(d, "IS_Harddisk")),
        ("Camera", lambda d: _f(d, "IS_Camera")),
        ("Adapter/Charger/Powerbank", lambda d: _f(d, "IS_Adapter") | _f(d, "IS_Charger")
                                                | _f(d, "IS_PowerBank")),
    ]


MAIN_DEFAULT = "Accessory and Others"


# ----------------------------------------------------------------- Sub --
def _adapter(d):   return _f(d, "IS_Adapter") | _f(d, "IS_Charger")
def _case(d):      return (_f(d, "IS_Case") | _f(d, "IS_Casing")
                           | _f(d, "IS_Protect") | _f(d, "IS_Bumper"))
def _film(d):      return _f(d, "IS_film")
def _cable(d):     return _f(d, "IS_Cable")
def _insurance(d): return _f(d, "IS_AppleCare") | _f(d, "IS_Insurance") | _f(d, "IS_Care")
def _other(d):     return (_f(d, "IS_Pin") | _f(d, "IS_Strap") | _f(d, "IS_Stand")
                           | _f(d, "IS_Dock") | _f(d, "IS_Accessory"))

# ของเดิมไม่สมมาตร Smart Watch ไม่มี Cable · HeadSet มีแค่ 2 กฎ ห้ามเติมให้ครบเอง
_ACCESSORY_OF = {
    "Smart Phone":      [("Adapter/Charger", _adapter), ("Case", _case), ("Film", _film),
                         ("Cable", _cable), ("Insurance", _insurance),
                         ("Other Accessory", _other)],
    "Tablet":           [("Adapter/Charger", _adapter), ("Case", _case), ("Film", _film),
                         ("Cable", _cable), ("Insurance", _insurance),
                         ("Other Accessory", _other)],
    "Smart Watch":      [("Adapter/Charger", _adapter), ("Case", _case), ("Film", _film),
                         ("Insurance", _insurance), ("Other Accessory", _other)],
    "HeadSet&Earpiece": [("Adapter/Charger", _adapter), ("Case", _case)],
}

_COMPONENT_OF = [("GraphicCard", "IS_GraphicCard"), ("PowerSupply", "IS_PowerSupply"),
                 ("Mainboard", "IS_Mainboard"), ("RAM", "IS_RAM"),
                 ("CPU", "IS_CPU"), ("Cooling System", "IS_Cooling")]


def sub_rules():
    """คืน [(label หรือ None, เงื่อนไข)] · None = ใช้ Product_Purpose + '-' + Main"""
    rules = []
    is_main = lambda d, p: d.Main_Product_Dimension == p

    for parent, accs in _ACCESSORY_OF.items():
        for suffix, cond in accs:
            rules.append((f"{parent} {suffix}",
                          lambda d, p=parent, c=cond: is_main(d, p) & c(d)))
        rules.append((f"{parent} Main&Other", lambda d, p=parent: is_main(d, p)))

    mk = lambda d: is_main(d, "Mouse&Keyboard")
    rules += [
        ("Mouse", lambda d: mk(d) & _f(d, "IS_Mouse") & ~_f(d, "IS_Keyboard")),
        ("Keyboard", lambda d: mk(d) & ~_f(d, "IS_Mouse") & _f(d, "IS_Keyboard")),
        ("Bundle Mouse&Keyboard", lambda d: mk(d) & _f(d, "IS_Mouse") & _f(d, "IS_Keyboard")),
        ("Software", lambda d: is_main(d, "Software")),
        ("Insurance", lambda d: is_main(d, "Insurance")),
        ("Console Gaming", lambda d: is_main(d, "Console Gaming")),
        (None, lambda d: is_main(d, "PC")),
        (None, lambda d: is_main(d, "Notebook")),
    ]
    for label, flag in _COMPONENT_OF:
        rules.append((label, lambda d, f=flag: is_main(d, "PC&Notebook Component") & _f(d, f)))
    return rules
