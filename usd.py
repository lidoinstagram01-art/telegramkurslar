import requests

def get_usd_rate():
    """USD kursini olish"""
    try:
        url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        response = requests.get(url, timeout=10).json()
        for item in response:
            if item['Ccy'] == 'USD':
                return float(item['Rate'])
        return 12800.0 # Zaxira qiymat
    except Exception as e:
        print(f"USD API xatosi: {e}")
        return 12800.0
