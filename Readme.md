# Stripe DATEV Exporter

## Environment

Uses Python's virtualenv. To setup initially:

```
virtualenv -p python3 venv
```

To activate in your current shell:

```
. venv/bin/activate
```

source env/bin/activate
python3 stripe-datev-cli.py download 2023 1

python3 -m unittest tests.helper_tests.test_creditnote_items

invoice in_1MYQ1wDc6Ds2E1iCLNnFkltZ 91506
['cn_1NApJgDc6Ds2E1iCpwuUWAhg 91506 91506']

# Export:

1. source env/bin/activate
2. python3 stripe-datev-cli.py download 2023 12

Check via Excel
=WENN(B3="S";WENN(LINKS(O3;9)="PRAP nach";A3*-1;A3);A3*-1)
