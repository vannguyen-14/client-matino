# routers/terms_and_conditions.py
from fastapi import APIRouter, Response
from typing import Dict, Any
import logging
import os

router = APIRouter(tags=["Terms and Conditions"])
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EN_PATH = os.path.join(BASE_DIR, "T&C-en.txt")
MY_PATH = os.path.join(BASE_DIR, "T&C-my.txt")

# Terms and Conditions content in English and Myanmar
TERMS_CONTENT = {
    "en": {
        "title": "Hero Saga - Terms and Conditions",
        "sections": [
            {
                "heading": "1. Game Description",
                "subsections": [
                    {
                        "title": "About the game",
                        "content": "In a colorful fantasy world once filled with peace and joy, darkness has spread as the evil forces of the underworld rise to conquer the kingdom. Villages have been destroyed, and mysterious creatures roam freely. Amidst the chaos, a young but brave adventurer Hero from his Saga sets out on a heroic journey to restore peace. Armed with courage and agility, the Hero must overcome deadly traps, outsmart monstrous enemies, and reclaim stolen treasures across various enchanted lands. His ultimate quest: defeat the Dark Lord and bring light back to the world."
                    }
                ]
            },
            {
                "heading": "2. Game Genre",
                "subsections": [
                    {
                        "title": "",
                        "content": "2D Side-Scrolling Platformer with Adventure elements. Designed for casual players who enjoy classic jump-and-run mechanics, Gold collection, and level-based challenges."
                    }
                ]
            },
            {
                "heading": "3. Prizes",
                "subsections": [
                    {
                        "title": "Weekly Prizes Plan",
                        "content": "Top 10 players who collect the most golds during a week have a chance to win prizes. Each week, from 00:00 on the first day to 23:59:59 on the last day, the top 10 players with the highest total points will be rewarded.",
                        "prize_table": [
                            {"rank": 1, "amount": "10,000 Loyalty Points", "quantity": 1},
                            {"rank": 2, "amount": "8,000 Loyalty Points", "quantity": 1},
                            {"rank": 3, "amount": "7,000 Loyalty Points", "quantity": 1},
                            {"rank": 4, "amount": "4,500 Loyalty Points", "quantity": 1},
                            {"rank": 5, "amount": "2,000 Loyalty Points", "quantity": 1},
                            {"rank": 6, "amount": "1,500 Loyalty Points", "quantity": 1},
                            {"rank": 7, "amount": "1,000 Loyalty Points", "quantity": 1},
                            {"rank": 8, "amount": "700 Loyalty Points", "quantity": 1},
                            {"rank": 9, "amount": "500 Loyalty Points", "quantity": 1},
                            {"rank": 10, "amount": "300 Loyalty Points", "quantity": 1}
                        ]
                    },
                    {
                        "title": "Monthly Prizes Plan",
                        "content": "There will be Monthly Leaderboard. Top 10 players who collect the golds during a month have a chance to win prizes. Each month, from 00:00 on the first day to 23:59:59 on the last day, the top 10 players with the highest total points will be rewarded.",
                        "prize_table": [
                            {"rank": 1, "amount": "1,000,000 MMK", "quantity": 1},
                            {"rank": 2, "amount": "500,000 MMK", "quantity": 1},
                            {"rank": 3, "amount": "300,000 MMK", "quantity": 1},
                            {"rank": 4, "amount": "200,000 MMK", "quantity": 1},
                            {"rank": 5, "amount": "100,000 MMK", "quantity": 1},
                            {"rank": 6, "amount": "50,000 MMK", "quantity": 1},
                            {"rank": 7, "amount": "40,000 MMK", "quantity": 1},
                            {"rank": 8, "amount": "30,000 MMK", "quantity": 1},
                            {"rank": 9, "amount": "20,000 MMK", "quantity": 1},
                            {"rank": 10, "amount": "10,000 MMK", "quantity": 1}
                        ]
                    },
                    {
                        "title": "How to Claim Rewards",
                        "content": "For Loyalty Points and Data MB prizes, Mytel system (Bonus Gate Way API) will be integrated and partner will add prizes to user directly according to rules. For Cash Rewards, it will be transferred to winner bank account which winner provided to Customer care Department after happy"
                    }
                ]
            },
            {
                "heading": "4. Acceptance of Terms",
                "subsections": [
                    {
                        "title": "",
                        "content": "By using the Game, you confirm that you have read, understood, and accepted these Terms. If you do not agree, please do not install or play the Game."
                    }
                ]
            },
            {
                "heading": "5. Virtual Items & Currencies",
                "subsections": [
                    {
                        "title": "",
                        "content": "All virtual coins, items, or upgrades have no real-world value. They cannot be exchanged, sold, or transferred to other users, inside or outside the Game."
                    }
                ]
            },
            {
                "heading": "6. User Conduct",
                "subsections": [
                    {
                        "title": "",
                        "content": "By playing the game, you agree not to:\n• Harass, threaten, or abuse other players.\n• Use the Game for illegal or commercial activities.\n• Post or share inappropriate, offensive, or infringing content.\n\nViolation may lead to temporary or permanent suspension of your account."
                    }
                ]
            },
            {
                "heading": "7. Account & Data",
                "subsections": [
                    {
                        "title": "",
                        "content": "Some versions of the Game may allow or require you to create an account. You are responsible for maintaining your login confidentiality. We may collect limited usage data (e.g., gameplay analytics, crash reports) as described in our Privacy Policy."
                    }
                ]
            },
            {
                "heading": "8. Updates & Maintenance",
                "subsections": [
                    {
                        "title": "",
                        "content": "We may release patches, updates, or new features to improve gameplay. These updates may be automatically installed. We reserve the right to modify, suspend, or discontinue parts of the Game at any time."
                    }
                ]
            },
            {
                "heading": "9. Disclaimer of Warranties",
                "subsections": [
                    {
                        "title": "",
                        "content": "The Game is provided \"as is\" and \"as available.\" We make no warranties of any kind regarding performance, reliability, or uninterrupted service. You use the Game at your own risk."
                    }
                ]
            },
            {
                "heading": "10. Limitation of Liability",
                "subsections": [
                    {
                        "title": "",
                        "content": "We shall not be liable for any direct, indirect, incidental, or consequential damages arising from your use of the Game, including data loss or device malfunction."
                    }
                ]
            },
            {
                "heading": "11. Termination",
                "subsections": [
                    {
                        "title": "",
                        "content": "We may suspend or terminate your access to the Game at any time if you breach these Terms. Upon termination, your right to play and all virtual items will be forfeited without compensation."
                    }
                ]
            },
            {
                "heading": "12. Governing Law",
                "subsections": [
                    {
                        "title": "",
                        "content": "These Terms shall be governed by and construed in accordance with the laws of Myanmar. Any disputes shall be subject to the exclusive jurisdiction of competent courts in that region."
                    }
                ]
            },
            {
                "heading": "13. How to Play",
                "subsections": [
                    {
                        "title": "",
                        "content": "Players control Martino using the on-screen joystick or arrow keys to move left or right. The gameplay is classic side-scrolling style with intuitive platformer controls:\n\n• Jump: Tap once to jump over obstacles or gaps.\n• Double Jump: Tap jump twice to reach higher platforms.\n• Attack: Jump onto enemies to defeat them (no weapons needed).\n• Collectibles: Gather Golds, power-ups, and hidden treasures scattered throughout each level.\n• Power-Ups: Certain blocks contain mushrooms or stars that grant speed boosts, invincibility, or bonus points.\n\nThe players also could use PC with movement buttons to move left or right, and enjoy as emotionally as playing of Playstation game in history."
                    }
                ]
            },
            {
                "heading": "14. How to Unsubscribe",
                "subsections": [
                    {
                        "title": "",
                        "content": "To cancel your subscription, just send OFF to 609 via SMS."
                    }
                ]
            }
        ]
    },
    "my": {
        "title": "Hero Saga - စည်းကမ်းချက်များနှင့် သတ်မှတ်ချက်များ",
        "sections": [
            {
                "heading": "၁။ နိဒါန်း",
                "subsections": [
                    {
                        "title": "၁.၁။ ဂိမ်းအကြောင်း",
                        "content": "တစ်ချိန်က ငြိမ်းချမ်းပြောင်ရွှင်မှုနဲ့ ပြည့်နှက်နေခဲ့တဲ့ ရောင်စုံစိတ်ကူးယဉ်လောကကြီးမှာ မှောင်မိုက်ခြင်းတွေ ပြန့်ပွားလာပြီး မြေအောက်လောကရဲ့ ဆိုးယုတ်သော အင်အားစုတွေက နိုင်ငံတော်ကို သိမ်းပိုက်ဖို့ ထလာကြပါတယ်။ ရွာတွေ ပျက်စီးခဲ့ပြီး ဆိုးဆိုးယုတ်ယုတ် အင်အားစုတွေ လွတ်လပ်စွာ ရှိနေကြပါတယ်။ ဒီလောကြပ်ကြီးမှာ ရဲရင့်သော စွန့်စားခန့်ခွဲသူ Hero သည် သူ့ရဲ့ Saga မှ ငြိမ်းချမ်းရေးကို ပြန်လည်ထူထောင်ရန် စွန့်စားခရီးကို စတင်ခဲ့ပါတယ်။ ရဲစွမ်းသတ္တိနှင့် လှုပ်လှုပ်ရှားရှားဖြင့် Hero သည် အသေအချောသော ထောင်ချောက်တွေကို ကျော်လွှားရမယ်၊ ဘီးရဲ့သက်သတ်တွေကို ထက်မြက်စွာ ရှာရမယ်၊ နှင့် မြောက်ဆန်ခဲ့တဲ့ ရတနာတွေကို တို့ယူရှာရမယ် ဖြစ်ပါတယ်။ သူ့ရဲ့ နောက်ဆုံးစိန်ခေါ်မှုက Dark Lord ကို ရှုံးနိမ့်အောင် လုပ်ပြီး ကမ္ဘာကြီးကို အလင်းရောင်ပြန်ပေးရမှာ ဖြစ်ပါတယ်။"
                    }
                ]
            },
            {
                "heading": "၂။ ဂိမ်းအမျိုးအစား",
                "subsections": [
                    {
                        "title": "",
                        "content": "စွန့်စားမှုဒြပ်စင်များပါသော 2D Side-Scrolling Platformer။ ဂန္ထဝင် jump-and-run စနစ်များ၊ ရွှေဆောင်ခြင်း၊ နှင့် အဆင့်အလိုက် စိန်ခေါ်မှုများကို နှစ်သက်သော ပေါ့ပေါ့ပါးပါး ကစားသူများအတွက် ဒီဇိုင်းထုတ်ထားပါသည်။"
                    }
                ]
            },
            {
                "heading": "၃။ ဆုများ",
                "subsections": [
                    {
                        "title": "အပတ်စဉ်ဆုများ အစီအစဉ်",
                        "content": "အပတ်စဉ် Leaderboard ရှိမည်ဖြစ်သည်။ တစ်ပတ်အတွင်း ရွှေအများဆုံး စုဆောင်းနိုင်သော ဒိပ်တန်းကစားသူ ၁၀ ဦးသည် ဆုများရရှိမှာဖြစ်သည်။ တစ်ပတ်လျှင် ပထမနေ့၏ 00:00 မှ နောက်ဆုံးနေ့၏ 23:59:59 အထိ စုစုပေါင်းရမှတ်အများဆုံး ဒိပ်တန်းကစားသူ ၁၀ ဦးကို ဆုချီးမြှင့်မည် ဖြစ်ပါသည်။",
                        "prize_table": [
                            {"rank": 1, "amount": "10,000 Loyalty Points", "quantity": 1},
                            {"rank": 2, "amount": "8,000 Loyalty Points", "quantity": 1},
                            {"rank": 3, "amount": "7,000 Loyalty Points", "quantity": 1},
                            {"rank": 4, "amount": "4,500 Loyalty Points", "quantity": 1},
                            {"rank": 5, "amount": "2,000 Loyalty Points", "quantity": 1},
                            {"rank": 6, "amount": "1,500 Loyalty Points", "quantity": 1},
                            {"rank": 7, "amount": "1,000 Loyalty Points", "quantity": 1},
                            {"rank": 8, "amount": "700 Loyalty Points", "quantity": 1},
                            {"rank": 9, "amount": "500 Loyalty Points", "quantity": 1},
                            {"rank": 10, "amount": "300 Loyalty Points", "quantity": 1}
                        ]
                    },
                    {
                        "title": "လစဉ်ဆုများ အစီအစဉ်",
                        "content": "လစဉ် Leaderboard ရှိမည်ဖြစ်သည်။ တစ်လအတွင်း ရွှေများ စုဆောင်းနိုင်သော ဒိပ်တန်းကစားသူ ၁၀ ဦးသည် ဆုများရရှိမှာဖြစ်သည်။ တစ်လလျှင် ပထမနေ့၏ 00:00 မှ နောက်ဆုံးနေ့၏ 23:59:59 အထိ စုစုပေါင်းရမှတ်အများဆုံး ဒိပ်တန်းကစားသူ ၁၀ ဦးကို ဆုချီးမြှင့်မည် ဖြစ်ပါသည်။",
                        "prize_table": [
                            {"rank": 1, "amount": "1,000,000 ကျပ်", "quantity": 1},
                            {"rank": 2, "amount": "500,000 ကျပ်", "quantity": 1},
                            {"rank": 3, "amount": "300,000 ကျပ်", "quantity": 1},
                            {"rank": 4, "amount": "200,000 ကျပ်", "quantity": 1},
                            {"rank": 5, "amount": "100,000 ကျပ်", "quantity": 1},
                            {"rank": 6, "amount": "50,000 ကျပ်", "quantity": 1},
                            {"rank": 7, "amount": "40,000 ကျပ်", "quantity": 1},
                            {"rank": 8, "amount": "30,000 ကျပ်", "quantity": 1},
                            {"rank": 9, "amount": "20,000 ကျပ်", "quantity": 1},
                            {"rank": 10, "amount": "10,000 ကျပ်", "quantity": 1}
                        ]
                    },
                    {
                        "title": "ဆုများရယူနည်း",
                        "content": "Loyalty Points နှင့် Data MB ဆုများအတွက် Mytel system (Bonus Gate Way API) ကို ပေါင်းစပ်ပြီး စည်းကမ်းချက်များအရ အသုံးပြုသူကို တိုက်ရိုက်ဆုများပေးမည်ဖြစ်ပါသည်။ ငွေသားဆုများအတွက် အနိုင်ရရှိသူ၏ ဘဏ်အကောင့်သို့ လွှဲပြောင်းပေးမည်ဖြစ်ပြီး အနိုင်ရရှိသူက Customer care Department သို့ ပေးအပ်ထားသော အချက်အလက်များအရ ပေးမည်ဖြစ်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၄။ စည်းကမ်းချက်များကို လက်ခံခြင်း",
                "subsections": [
                    {
                        "title": "",
                        "content": "ဂိမ်းကို အသုံးပြုခြင်းဖြင့် ဤစည်းကမ်းချက်များကို ဖတ်ရှုပြီး နားလည်ကာ လက်ခံကြောင်း အတည်ပြုပါသည်။ သဘောမတူပါက ဂိမ်းကို ထည့်သွင်းခြင်း သို့မဟုတ် ကစားခြင်း မပြုလုပ်ပါနှင့်။"
                    }
                ]
            },
            {
                "heading": "၅။ Virtual Items & Currencies",
                "subsections": [
                    {
                        "title": "",
                        "content": "Virtual coins၊ items သို့မဟုတ် upgrades များသည် အစစ်အမှန်တန်ဖိုး မရှိပါ။ ၎င်းတို့ကို ဂိမ်းအတွင်း သို့မဟုတ် ဂိမ်းအပြင်တွင် အခြားအသုံးပြုသူများသို့ လဲလှယ်ခြင်း၊ ရောင်းချခြင်း သို့မဟုတ် လွှဲပြောင်းခြင်း မပြုလုပ်နိုင်ပါ။"
                    }
                ]
            },
            {
                "heading": "၆။ အသုံးပြုသူအပြုအမူ",
                "subsections": [
                    {
                        "title": "",
                        "content": "ဂိမ်းကစားခြင်းဖြင့် အောက်ပါတို့ကို မလုပ်ရန် သဘောတူပါသည်:\n• အခြားကစားသူများကို နှောင့်ယှက်ခြင်း၊ ခြိမ်းခြောက်ခြင်း သို့မဟုတ် အလွဲသုံးစားလုပ်ခြင်း။\n• ဥပဒေမဲ့ သို့မဟုတ် စီးပွားရေးလုပ်ငန်းများအတွက် ဂိမ်းကို အသုံးပြုခြင်း။\n• မသင့်လျော်သော၊ စော်ကားသော သို့မဟုတ် ချိုးဖောက်သော အကြောင်းအရာများ တင်ခြင်း သို့မဟုတ် မျှဝေခြင်း။\n\nချိုးဖောက်မှုများသည် သင့်အကောင့်ကို ယာယီ သို့မဟုတ် အမြဲတမ်း ရပ်ဆိုင်းခြင်းကို ဖြစ်စေနိုင်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၇။ အကောင့်နှင့်ဒေတာ",
                "subsections": [
                    {
                        "title": "",
                        "content": "ဂိမ်း၏ အချို့ဗားရှင်းများသည် အကောင့်ဖန်တီးရန် ခွင့်ပြုခြင်း သို့မဟုတ် လိုအပ်နိုင်ပါသည်။ သင့်အကောင့် login လျှို့ဝှက်ချက်ကို ထိန်းသိမ်းရန် သင်တာဝန်ရှိပါသည်။ ကျွန်ုပ်တို့သည် ကန့်သတ်ထားသော အသုံးပြုမှုဒေတာ (ဥပမာ gameplay analytics၊ crash reports) များကို ကျွန်ုပ်တို့၏ Privacy Policy တွင် ဖော်ပြထားသည့်အတိုင်း စုဆောင်းနိုင်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၈။ Updates & Maintenance",
                "subsections": [
                    {
                        "title": "",
                        "content": "ဂိမ်းကစားမှုကို တိုးတက်ကောင်းမွန်စေရန် patches၊ updates သို့မဟုတ် အင်္ဂါရပ်သစ်များကို ထုတ်ပြန်နိုင်ပါသည်။ ဤ updates များကို အလိုအလျောက် ထည့်သွင်းနိုင်ပါသည်။ ကျွန်ုပ်တို့သည် မည်သည့်အချိန်တွင်မဆို ဂိမ်း၏ အစိတ်အပိုင်းများကို ပြင်ဆင်ခြင်း၊ ရပ်ဆိုင်းခြင်း သို့မဟုတ် ရပ်တန့်ခြင်းပြုလုပ်ပိုင်ခွင့် ရှိပါသည်။"
                    }
                ]
            },
            {
                "heading": "၉။ အာမခံချက်များကို ငြင်းဆိုခြင်း",
                "subsections": [
                    {
                        "title": "",
                        "content": "ဂိမ်းကို \"လက်ရှိအတိုင်း\" နှင့် \"ရရှိနိုင်သည့်အတိုင်း\" ပေးထားပါသည်။ စွမ်းဆောင်ရည်၊ ယုံကြည်စိတ်ချရမှု သို့မဟုတ် မရပ်တန့်သော ဝန်ဆောင်မှုနှင့်ပတ်သက်၍ မည်သည့်အာမခံချက်မှ မပေးပါ။ ဂိမ်းကို ကစားခြင်းသည် သင့်ကိုယ်ပိုင်အန္တရာယ်ဖြင့် ဖြစ်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၁၀။ တာဝန်ခံမှု ကန့်သတ်ချက်",
                "subsections": [
                    {
                        "title": "",
                        "content": "သင့်ဂိမ်းအသုံးပြုမှုမှ ဖြစ်ပေါ်လာသော တိုက်ရိုက် သို့မဟုတ် သွယ်ဝိုက်သော၊ မတော်တဆ သို့မဟုတ် အကျိုးဆက်ပျက်စီးမှုများအတွက် ကျွန်ုပ်တို့သည် တာဝန်မရှိပါ။ ဒေတာဆုံးရှုံးမှု သို့မဟုတ် စက်ပစ္စည်းပျက်စီးမှုများလည်း ပါဝင်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၁၁။ ရပ်ဆိုင်းခြင်း",
                "subsections": [
                    {
                        "title": "",
                        "content": "သင်သည် ဤစည်းကမ်းချက်များကို ချိုးဖောက်ပါက ကျွန်ုပ်တို့သည် မည်သည့်အချိန်တွင်မဆို သင့်ဂိမ်းအသုံးပြုခွင့်ကို ရပ်ဆိုင်း သို့မဟုတ် ရပ်တန့်နိုင်ပါသည်။ ရပ်ဆိုင်းပြီးနောက် သင့်ကစားခွင့်နှင့် virtual items အားလုံးကို လျော်ကြေးမရှိဘဲ ဆုံးရှုံးရမည်ဖြစ်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၁၂။ အုပ်ချုပ်သောဥပဒေ",
                "subsections": [
                    {
                        "title": "",
                        "content": "ဤစည်းကမ်းချက်များကို မြန်မာနိုင်ငံ၏ ဥပဒေများနှင့်အညီ အုပ်ချုပ်ပြီး အဓိပ္ပာယ်ဖွင့်မည်ဖြစ်ပါသည်။ မည်သည့်အငြင်းပွားမှုမဆို ထိုဒေသရှိ သက်ဆိုင်ရာတရားရုံးများ၏ သီးသန့်စီရင်ပိုင်ခွင့်အောက်တွင် ရှိမည်ဖြစ်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၁၃။ ကစားနည်း",
                "subsections": [
                    {
                        "title": "",
                        "content": "ကစားသူများသည် Martino ကို မျက်နှာပြင်ပေါ်ရှိ joystick သို့မဟုတ် မြှားတလုတ်များကို အသုံးပြု၍ ဘယ်ညာရွှေ့လျားနိုင်ပါသည်။ ဂိမ်းကစားနည်းသည် နားလည်လွယ်သော platformer ဒိန်းထိုပ်များဖြင့် ဂန္ထဝင် side-scrolling ပုံစံဖြစ်ပါသည်:\n\n• ခုန်ခြင်း: အတားအဆီးများ သို့မဟုတ် ကွက်လပ်များကို ကျော်ရန် တစ်ကြိမ်ထိပါ။\n• နှစ်ကြိမ်ခုန်: မြင့်မားသော ပလက်ဖောင်းများသို့ ရောက်ရန် နှစ်ကြိမ်ခုန်ပါ။\n• တိုက်ခိုက်တိုက်ခြင်း: ရန်သူများကို အနိုင်ယူရန် သူတို့အပေါ်သို့ ခုန်တက်ပါ (လက်နက်မလိုပါ)။\n• စုဆောင်းရမည့်ပစ္စည်းများ: အဆင့်တစ်တိုင်းတွင် ကွဲထွက်နေသော ရွှေများ၊ power-ups နှင့် တဖန်းဆန်းရတနာများကို စုဆောင်းပါ။\n• Power-Ups: အချို့သော ဘလောက်များတွင် မှို့များ သို့မဟုတ် ကြယ်များ ပါရှိပြီး အရှိန်မြင့်တင်ခြင်း၊ မဖျက်ဆီးနိုင်ခြင်း သို့မဟုတ် ဘောနပ်စ်ရမှတ်များ ပေးပါသည်။\n\nကစားသူများသည် PC ဖြင့်လည်း ရွှေ့လျားတလုတ်များဖြင့် ဘယ်ညာရွှေ့လျားနိုင်ပြီး သမိုင်းတွင် Playstation ဂိမ်းကစားသကဲ့သို့ စိတ်လှုပ်ရှားစွာ တစ်ခါးစားနိုင်ပါသည်။"
                    }
                ]
            },
            {
                "heading": "၁၄။ Unsubscribe လုပ်နည်း",
                "subsections": [
                    {
                        "title": "",
                        "content": "သင့် subscription ကို ပယ်ဖျက်ရန် 609 သို့ OFF ဟု SMS ပို့ပါ။"
                    }
                ]
            }
        ]
    }
}


@router.get("/terms-and-conditions")
async def get_terms_and_conditions(lang: str = "en") -> Dict[str, Any]:
    """
    Get Terms and Conditions for Hero Saga game (JSON version)
    """
    logger.info(f"Terms and Conditions requested in language: {lang}")
    if lang not in ["en", "my"]:
        lang = "en"
        logger.warning(f"Invalid language requested, defaulting to English")

    from .terms_and_conditions_data import TERMS_CONTENT  # optional: nếu bạn tách dữ liệu ra file riêng
    return {
        "success": True,
        "language": lang,
        "data": TERMS_CONTENT[lang],
    }


@router.get("/terms-and-conditions/both")
async def get_terms_both_languages() -> Dict[str, Any]:
    """
    Get Terms and Conditions in both English and Myanmar (JSON)
    """
    from .terms_and_conditions_data import TERMS_CONTENT
    logger.info("Terms and Conditions requested in both languages")
    return {
        "success": True,
        "data": {
            "english": TERMS_CONTENT["en"],
            "myanmar": TERMS_CONTENT["my"],
        },
    }


@router.get("/terms-and-conditions/html")
async def get_terms_html(lang: str = "en"):
    """
    Return Terms and Conditions as full HTML page (for frontend display)
    """
    logger.info(f"Returning HTML Terms and Conditions for language: {lang}")

    # Validate lang
    if lang not in ["en", "my"]:
        lang = "en"

    # Read corresponding HTML file
    file_path = EN_PATH if lang == "en" else MY_PATH
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read T&C file for {lang}: {e}")
        return Response(
            content=f"<h1>Error</h1><p>Cannot load Terms and Conditions ({lang}).</p>",
            media_type="text/html",
            status_code=500,
        )

    # Wrap with minimal HTML page for display
    full_html = f"""
    <!DOCTYPE html>
    <html lang="{lang}">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Hero Saga - Terms and Conditions</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          margin: 40px;
          color: #9c5a3a;
          line-height: 1.6;
        }}
        h1, h2, h3 {{
          color: #9c5a3a;
          margin-top: 1.2em;
        }}
        table {{
          border-collapse: collapse;
          width: 100%;
          margin: 12px 0;
        }}
        th, td {{
          border: 1px solid #9c5a3a;
          padding: 8px;
        }}
        th {{
          background-color: #f8f3ef;
        }}
        ul {{
          margin-left: 20px;
        }}
        p {{
          margin: 6px 0;
        }}
      </style>
    </head>
    <body>
      {html_content}
    </body>
    </html>
    """

    return Response(content=full_html, media_type="text/html")