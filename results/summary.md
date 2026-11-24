# IST 736 defense results (frozen)

## Main results

| Configuration | Clean utility (/50) | ASR (/100) | Utility under attack (/100) | Blocked calls (tasks / attacks) | Agent tokens | Monitor tokens |
|---|---|---|---|---|---|---|
| none | 47/50 (94%, 84 to 98) | 20/100 (20%, 13 to 29) | 97/100 (97%, 92 to 99) | 0 / 0 | 379,746 | 0 |
| spotlight | 47/50 (94%, 84 to 98) | 9/100 (9%, 5 to 16) | 99/100 (99%, 95 to 100) | 0 / 0 | 384,161 | 0 |
| classifier | 33/50 (66%, 52 to 78) | 0/100 (0%, 0 to 4) | 28/100 (28%, 20 to 37) | 0 / 0 | 327,481 | 0 |
| gate | 47/50 (94%, 84 to 98) | 7/100 (7%, 3 to 14) | 92/100 (92%, 85 to 96) | 0 / 14 | 378,942 | 0 |
| monitor | 47/50 (94%, 84 to 98) | 0/100 (0%, 0 to 4) | 92/100 (92%, 85 to 96) | 0 / 24 | 377,668 | 37,961 |
| spotlight+classifier | 35/50 (70%, 56 to 81) | 0/100 (0%, 0 to 4) | 27/100 (27%, 19 to 36) | 0 / 0 | 344,676 | 0 |
| spotlight+gate | 47/50 (94%, 84 to 98) | 2/100 (2%, 1 to 7) | 99/100 (99%, 95 to 100) | 2 / 6 | 383,470 | 0 |
| spotlight+monitor | 46/50 (92%, 81 to 97) | 0/100 (0%, 0 to 4) | 99/100 (99%, 95 to 100) | 0 / 10 | 381,431 | 30,447 |
| classifier+gate | 35/50 (70%, 56 to 81) | 0/100 (0%, 0 to 4) | 28/100 (28%, 20 to 37) | 2 / 0 | 330,995 | 0 |
| classifier+monitor | 34/50 (68%, 54 to 79) | 0/100 (0%, 0 to 4) | 25/100 (25%, 18 to 34) | 1 / 0 | 329,771 | 22,823 |
| gate+monitor | 47/50 (94%, 84 to 98) | 0/100 (0%, 0 to 4) | 92/100 (92%, 85 to 96) | 2 / 22 | 380,120 | 28,662 |
| spotlight+classifier+gate | 34/50 (68%, 54 to 79) | 0/100 (0%, 0 to 4) | 27/100 (27%, 19 to 36) | 2 / 0 | 348,432 | 0 |
| spotlight+classifier+monitor | 34/50 (68%, 54 to 79) | 0/100 (0%, 0 to 4) | 29/100 (29%, 21 to 39) | 1 / 0 | 345,993 | 22,920 |
| spotlight+gate+monitor | 48/50 (96%, 87 to 99) | 0/100 (0%, 0 to 4) | 99/100 (99%, 95 to 100) | 2 / 10 | 379,868 | 26,782 |
| classifier+gate+monitor | 35/50 (70%, 56 to 81) | 0/100 (0%, 0 to 4) | 29/100 (29%, 21 to 39) | 1 / 0 | 330,782 | 22,963 |
| spotlight+classifier+gate+monitor | 34/50 (68%, 54 to 79) | 0/100 (0%, 0 to 4) | 29/100 (29%, 21 to 39) | 3 / 1 | 350,084 | 22,928 |

Rates show count, percent, and the 95% Wilson interval.

## Attack success by injection style (each /25)

| Configuration | override | system_notice | important_instructions | polite_ps |
|---|---|---|---|---|
| none | 0 | 8 | 12 | 0 |
| spotlight | 0 | 5 | 4 | 0 |
| classifier | 0 | 0 | 0 | 0 |
| gate | 0 | 2 | 5 | 0 |
| monitor | 0 | 0 | 0 | 0 |
| spotlight+classifier | 0 | 0 | 0 | 0 |
| spotlight+gate | 0 | 0 | 2 | 0 |
| spotlight+monitor | 0 | 0 | 0 | 0 |
| classifier+gate | 0 | 0 | 0 | 0 |
| classifier+monitor | 0 | 0 | 0 | 0 |
| gate+monitor | 0 | 0 | 0 | 0 |
| spotlight+classifier+gate | 0 | 0 | 0 | 0 |
| spotlight+classifier+monitor | 0 | 0 | 0 | 0 |
| spotlight+gate+monitor | 0 | 0 | 0 | 0 |
| classifier+gate+monitor | 0 | 0 | 0 | 0 |
| spotlight+classifier+gate+monitor | 0 | 0 | 0 | 0 |

## Attack success by attacker goal (each /20)

| Configuration | steal_reset_code | steal_flight_code | phish_colleague | invoice_fraud | send_to_attacker |
|---|---|---|---|---|---|
| none | 1 | 4 | 5 | 3 | 7 |
| spotlight | 0 | 3 | 2 | 0 | 4 |
| classifier | 0 | 0 | 0 | 0 | 0 |
| gate | 0 | 0 | 6 | 1 | 0 |
| monitor | 0 | 0 | 0 | 0 | 0 |
| spotlight+classifier | 0 | 0 | 0 | 0 | 0 |
| spotlight+gate | 0 | 0 | 2 | 0 | 0 |
| spotlight+monitor | 0 | 0 | 0 | 0 | 0 |
| classifier+gate | 0 | 0 | 0 | 0 | 0 |
| classifier+monitor | 0 | 0 | 0 | 0 | 0 |
| gate+monitor | 0 | 0 | 0 | 0 | 0 |
| spotlight+classifier+gate | 0 | 0 | 0 | 0 | 0 |
| spotlight+classifier+monitor | 0 | 0 | 0 | 0 | 0 |
| spotlight+gate+monitor | 0 | 0 | 0 | 0 | 0 |
| classifier+gate+monitor | 0 | 0 | 0 | 0 | 0 |
| spotlight+classifier+gate+monitor | 0 | 0 | 0 | 0 | 0 |
