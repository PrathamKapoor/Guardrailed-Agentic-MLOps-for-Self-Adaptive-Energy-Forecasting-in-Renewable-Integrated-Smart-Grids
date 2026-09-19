# H24 model evolution

| Target | Evidence | Role | MAE |
| --- | --- | --- | --- |
| load | best naive | benchmark | 211.392 |
| load | RTS DAY_AHEAD | benchmark | 126.613 |
| load | untuned classical | F01-F06 retrospective | 179.458 |
| load | tuned classical | SEARCH F01-F04 | 389.306 |
| load | untuned PyTorch MLP | matched F05-F06 | 294.864 |
| load | tuned PyTorch MLP | POST-HPO F05-F06 | 320.234 |
| wind | best naive | benchmark | 586.542 |
| wind | RTS DAY_AHEAD | benchmark | 269.006 |
| wind | untuned classical | F01-F06 retrospective | 513.907 |
| wind | tuned classical | SEARCH F01-F04 | 570.656 |
| wind | untuned PyTorch MLP | matched F05-F06 | 518.731 |
| wind | tuned PyTorch MLP | POST-HPO F05-F06 | 522.112 |
| pv | daily persistence | benchmark | 33.765 |
| pv | RTS DAY_AHEAD | benchmark | 48.795 |
| pv | untuned classical | F01-F06 retrospective | 36.588 |
| pv | tuned classical | SEARCH F01-F04 | 49.003 |
| pv | untuned PyTorch MLP | matched F05-F06 | 49.255 |
| pv | tuned PyTorch MLP | POST-HPO F05-F06 | 55.611 |

Search and post-HPO evaluation roles are intentionally not conflated.
