import requests

def get_usd_rate():
    """Anorbank yoki tijorat bankining USD sotib olish kursini olish"""
    try:
        # Anorbank rasmiy kurslar API manzili
        url = "https://anorbank.uz/api/v1/rates" # yoki CBU o'rniga bank API
        response = requests.get(url, timeout=10).json()
        
        # Agar Anorbank API ishlamasa, CBU kursidan biroz pastroq (sotib olish) qilib olamiz
        # Lekin keling, Anorbank ma'lumotlarini o'qib ko'ramiz:
        for item in response.get('data', []):
            if item.get('currency') == 'USD':
                return float(item.get('buy', 11960.0))
                
    except Exception as e:
        print(f"Bank API xatosi: {e}")
    
    # Zaxira sifatida Markaziy Bank kursidan sotib olish qiymatini chiqarish (masalan, MB - 60 so'm)
    try:
        cbu_url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        cbu_res = requests.get(cbu_url, timeout=10).json()
        for item in cbu_res:
            if item['Ccy'] == 'USD':
                mb_rate = float(item['Rate'])
                # Odatda tijorat banklari sotib olish kursi MB dan biroz past bo'ladi
                return mb_rate - 60.0 
    except:
        pass

    return 11960.0 # Keskin holatdagi zaxira qiymat
