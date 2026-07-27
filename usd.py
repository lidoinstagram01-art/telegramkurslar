import requests

def get_all_usd_rates():
    """USD uchun MB kursi, Sotib olish va Sotish kurslarini olish"""
    rates = {
        "mb": None,       # Markaziy bank rasmiy kursi
        "buy": None,      # Bank sizdan sotib olishi
        "sell": None      # Bank sizga sotishi
    }
    
    # 1. MB rasmiy kursini olish
    try:
        cbu_url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        cbu_res = requests.get(cbu_url, timeout=5).json()
        for item in cbu_res:
            if item['Ccy'] == 'USD':
                rates["mb"] = float(item['Rate'])
                break
    except Exception as e:
        print(f"CBU API xatosi: {e}")

    # 2. NBU (Milliy bank) Commercial kurslarini olish
    try:
        nbu_url = "https://nbu.uz/uz/exchange-rates/json/"
        nbu_res = requests.get(nbu_url, timeout=5).json()
        for item in nbu_res:
            if item['code'] == 'USD':
                # nbu.uz ba'zan kurs bo'lmasa bo'sh matn qaytarishi mumkin
                rates["buy"] = float(item['nbu_buy_price']) if item.get('nbu_buy_price') else rates["mb"]
                rates["sell"] = float(item['nbu_cell_price']) if item.get('nbu_cell_price') else rates["mb"]
                break
    except Exception as e:
        print(f"NBU API xatosi: {e}")
        # Agar NBU xato bersa, zaxira sifatida MB kursini ishlatamiz
        rates["buy"] = rates["mb"]
        rates["sell"] = rates["mb"]

    return rates
