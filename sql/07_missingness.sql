-- 07_missingness.sql
-- Measure variable coverage in the first 24-hour trajectory dataset

SELECT
    label,
    source,
    COUNT(*) AS n_measurements,
    COUNT(DISTINCT stay_id) AS n_stays,
    ROUND(
        COUNT(DISTINCT stay_id)::numeric
        / (SELECT COUNT(*) FROM mimiciv_derived.cohort_icu_adult) * 100,
        2
    ) AS coverage_percent
FROM mimiciv_derived.trajectory_first24h
GROUP BY label, source
ORDER BY coverage_percent DESC, n_measurements DESC;


/*

                   label                    | source | n_measurements | n_stays | coverage_percent 
--------------------------------------------+--------+----------------+---------+------------------
 Heart Rate                                 | vital  |        2096007 |   74752 |            99.90
 O2 saturation pulseoxymetry                | vital  |        2052876 |   74731 |            99.87
 Respiratory Rate                           | vital  |        2071233 |   74615 |            99.71
 Glucose                                    | lab    |         243415 |   73659 |            98.44
 Chloride                                   | lab    |         165555 |   73648 |            98.42
 Sodium                                     | lab    |         162520 |   73645 |            98.42
 Creatinine                                 | lab    |         160101 |   73629 |            98.40
 Urea Nitrogen                              | lab    |         159639 |   73616 |            98.38
 Bicarbonate                                | lab    |         159294 |   73617 |            98.38
 Potassium                                  | lab    |         166091 |   73606 |            98.37
 Anion Gap                                  | lab    |         157789 |   73545 |            98.28
 Hematocrit                                 | lab    |         184319 |   73381 |            98.06
 Hemoglobin                                 | lab    |         207276 |   73301 |            97.96
 Platelet Count                             | lab    |         162552 |   73274 |            97.92
 White Blood Cells                          | lab    |         159414 |   73269 |            97.92
 Red Blood Cells                            | lab    |         159239 |   73256 |            97.90
 MCV                                        | lab    |         159235 |   73255 |            97.90
 MCHC                                       | lab    |         159242 |   73248 |            97.89
 MCH                                        | lab    |         159197 |   73245 |            97.88
 RDW                                        | lab    |         159096 |   73210 |            97.84
 Magnesium                                  | lab    |         146571 |   71301 |            95.29
 Temperature Fahrenheit                     | vital  |         467790 |   69629 |            93.05
 Phosphate                                  | lab    |         138419 |   68588 |            91.66
 Calcium, Total                             | lab    |         137319 |   67981 |            90.85
 Non Invasive Blood Pressure mean           | vital  |        1344022 |   67434 |            90.12
 Non Invasive Blood Pressure systolic       | vital  |        1345335 |   67425 |            90.11
 Non Invasive Blood Pressure diastolic      | vital  |        1345047 |   67415 |            90.09
 PT                                         | lab    |         119839 |   63030 |            84.23
 INR(PT)                                    | lab    |         119802 |   63027 |            84.23
 PTT                                        | lab    |         123793 |   62512 |            83.54
 pH                                         | lab    |         216980 |   52021 |            69.52
 pO2                                        | lab    |         187275 |   44985 |            60.12
 Base Excess                                | lab    |         187084 |   44985 |            60.12
 pCO2                                       | lab    |         187080 |   44979 |            60.11
 Calculated Total CO2                       | lab    |         187077 |   44979 |            60.11
 Lactate                                    | lab    |         132547 |   44183 |            59.05
 RDW-SD                                     | lab    |          91385 |   39736 |            53.10
 H                                          | lab    |          93760 |   34749 |            46.44
 L                                          | lab    |          93759 |   34748 |            46.44
 I                                          | lab    |          93758 |   34748 |            46.44
 Asparate Aminotransferase (AST)            | lab    |          50218 |   34311 |            45.85
 Alanine Aminotransferase (ALT)             | lab    |          49770 |   33996 |            45.43
 Alkaline Phosphatase                       | lab    |          49376 |   33900 |            45.30
 Bilirubin, Total                           | lab    |          49734 |   33820 |            45.20
 Free Calcium                               | lab    |         102413 |   30527 |            40.80
 Arterial Blood Pressure mean               | vital  |         723725 |   29412 |            39.31
 Arterial Blood Pressure diastolic          | vital  |         720514 |   29199 |            39.02
 Arterial Blood Pressure systolic           | vital  |         720624 |   29191 |            39.01
 Lymphocytes                                | lab    |          33356 |   28168 |            37.64
 Monocytes                                  | lab    |          32560 |   27763 |            37.10
 Eosinophils                                | lab    |          31654 |   27372 |            36.58
 Basophils                                  | lab    |          31200 |   27137 |            36.27
 Neutrophils                                | lab    |          31067 |   27058 |            36.16
 Lactate Dehydrogenase (LD)                 | lab    |          28710 |   21514 |            28.75
 Potassium, Whole Blood                     | lab    |          81352 |   21436 |            28.65
 Albumin                                    | lab    |          27215 |   21310 |            28.48
 Oxygen Saturation                          | lab    |          64266 |   21244 |            28.39
 Creatine Kinase, MB Isoenzyme              | lab    |          32835 |   18278 |            24.43
 Creatine Kinase (CK)                       | lab    |          30334 |   18224 |            24.35
 Fibrinogen, Functional                     | lab    |          28806 |   17925 |            23.95
 Sodium, Whole Blood                        | lab    |          42685 |   17127 |            22.89
 Hematocrit, Calculated                     | lab    |          45174 |   16229 |            21.69
 Specific Gravity                           | lab    |          17079 |   15782 |            21.09
 Absolute Lymphocyte Count                  | lab    |          17651 |   15461 |            20.66
 Absolute Eosinophil Count                  | lab    |          17475 |   15373 |            20.54
 Absolute Neutrophil Count                  | lab    |          17475 |   15371 |            20.54
 Absolute Basophil Count                    | lab    |          17473 |   15371 |            20.54
 Absolute Monocyte Count                    | lab    |          17473 |   15371 |            20.54
 Troponin T                                 | lab    |          29378 |   14919 |            19.94
 Chloride, Whole Blood                      | lab    |          24215 |   14847 |            19.84
 Temperature                                | lab    |          26013 |   13655 |            18.25
 Immature Granulocytes                      | lab    |          13076 |   11945 |            15.96
 WBC                                        | lab    |          11423 |   10932 |            14.61
 RBC                                        | lab    |          11098 |   10651 |            14.23
 Oxygen                                     | lab    |          18170 |   10364 |            13.85
 Epithelial Cells                           | lab    |          10467 |   10040 |            13.42
 Protein                                    | lab    |          10108 |    9573 |            12.79
 PEEP                                       | lab    |          15680 |    8723 |            11.66
 Tidal Volume                               | lab    |          13027 |    7387 |             9.87
 Temperature Celsius                        | vital  |         129453 |    7064 |             9.44
 Thyroid Stimulating Hormone                | lab    |           7078 |    6897 |             9.22
 Creatinine, Urine                          | lab    |           7283 |    6720 |             8.98
 Bands                                      | lab    |           7906 |    6555 |             8.76
 Triglycerides                              | lab    |           6818 |    6329 |             8.46
 Metamyelocytes                             | lab    |           7095 |    5893 |             7.88
 Myelocytes                                 | lab    |           6922 |    5753 |             7.69
 Sodium, Urine                              | lab    |           6347 |    5700 |             7.62
 Atypical Lymphocytes                       | lab    |           6759 |    5620 |             7.51
 Lipase                                     | lab    |           6465 |    5481 |             7.32
 % Hemoglobin A1c                           | lab    |           5557 |    5438 |             7.27
 Osmolality, Urine                          | lab    |           6486 |    5419 |             7.24
 eAG                                        | lab    |           5255 |    5140 |             6.87
 Hyaline Casts                              | lab    |           4875 |    4755 |             6.35
 CK-MB Index                                | lab    |           8394 |    4595 |             6.14
 Cholesterol, Total                         | lab    |           4575 |    4453 |             5.95
 Cholesterol, HDL                           | lab    |           4466 |    4356 |             5.82
 Urea Nitrogen, Urine                       | lab    |           4542 |    4343 |             5.80
 Cholesterol Ratio (Total/HDL)              | lab    |           4423 |    4320 |             5.77
 Cholesterol, LDL, Calculated               | lab    |           4242 |    4149 |             5.54
 Amylase                                    | lab    |           4874 |    4076 |             5.45
 Potassium, Urine                           | lab    |           4512 |    4030 |             5.39
 Vancomycin                                 | lab    |           4257 |    3909 |             5.22
 Ferritin                                   | lab    |           3927 |    3705 |             4.95
 Osmolality, Measured                       | lab    |           6273 |    3422 |             4.57
 Chloride, Urine                            | lab    |           3788 |    3410 |             4.56
 Iron                                       | lab    |           3350 |    3226 |             4.31
 Transferrin                                | lab    |           3162 |    3073 |             4.11
 Iron Binding Capacity, Total               | lab    |           3147 |    3060 |             4.09
 Nucleated Red Cells                        | lab    |           3497 |    2978 |             3.98
 Haptoglobin                                | lab    |           3300 |    2942 |             3.93
 Required O2                                | lab    |           4257 |    2893 |             3.87
 Ketone                                     | lab    |           3045 |    2895 |             3.87
 Alveolar-arterial Gradient                 | lab    |           4251 |    2891 |             3.86
 Polys                                      | lab    |           3149 |    2685 |             3.59
 Urobilinogen                               | lab    |           2743 |    2662 |             3.56
 Bilirubin, Direct                          | lab    |           4206 |    2649 |             3.54
 NTproBNP                                   | lab    |           2608 |    2530 |             3.38
 Bilirubin, Indirect                        | lab    |           3973 |    2462 |             3.29
 Reticulocyte Count, Automated              | lab    |           2475 |    2341 |             3.13
 O2 Flow                                    | lab    |           2425 |    2078 |             2.78
 Cortisol                                   | lab    |           2482 |    2010 |             2.69
 C-Reactive Protein                         | lab    |           2127 |    1974 |             2.64
 Reticulocyte Count, Absolute               | lab    |           1709 |    1608 |             2.15
 Calculated Bicarbonate, Whole Blood        | lab    |           2021 |    1561 |             2.09
 HPE1                                       | lab    |           1602 |    1552 |             2.07
 Monos                                      | lab    |           1656 |    1501 |             2.01
 HPE7                                       | lab    |           1501 |    1456 |             1.95
 Vitamin B12                                | lab    |           1463 |    1442 |             1.93
 Phenytoin                                  | lab    |           1905 |    1433 |             1.92
 HPE3                                       | lab    |           1412 |    1371 |             1.83
 Protein, Total                             | lab    |           1398 |    1334 |             1.78
 Granular Casts                             | lab    |           1291 |    1266 |             1.69
 Uric Acid                                  | lab    |           2125 |    1216 |             1.63
 Macrophage                                 | lab    |           1342 |    1217 |             1.63
 Thyroxine (T4), Free                       | lab    |           1165 |    1144 |             1.53
 UTX4                                       | lab    |           1090 |    1084 |             1.45
 UTX5                                       | lab    |           1089 |    1083 |             1.45
 UTX2                                       | lab    |           1082 |    1076 |             1.44
 UTX1                                       | lab    |           1077 |    1071 |             1.43
 D-Dimer                                    | lab    |           1273 |    1061 |             1.42
 UTX7                                       | lab    |           1071 |    1065 |             1.42
 UTX3                                       | lab    |           1069 |    1061 |             1.42
 UTX6                                       | lab    |           1024 |    1018 |             1.36
 tacroFK                                    | lab    |           1094 |     979 |             1.31
 ARCH-1                                     | lab    |            898 |     884 |             1.18
 Total Protein, Urine                       | lab    |            870 |     846 |             1.13
 Creatinine, Whole Blood                    | lab    |           1135 |     809 |             1.08
 Folate                                     | lab    |            732 |     723 |             0.97
 Immunoglobulin G                           | lab    |            742 |     721 |             0.96
 Protein/Creatinine Ratio                   | lab    |            740 |     722 |             0.96
 STX6                                       | lab    |            727 |     707 |             0.94
 Globulin                                   | lab    |            722 |     702 |             0.94
 Estimated GFR (CKD- EPI Refit)             | lab    |            863 |     698 |             0.93
 Digoxin                                    | lab    |            708 |     644 |             0.86
 Thyroxine (T4)                             | lab    |            662 |     645 |             0.86
 Lymphs                                     | lab    |            860 |     611 |             0.82
 Total Nucleated Cells, CSF                 | lab    |            859 |     612 |             0.82
 Immunoglobulin A                           | lab    |            632 |     613 |             0.82
 RBC, CSF                                   | lab    |            853 |     609 |             0.81
 Total Protein, CSF                         | lab    |            605 |     599 |             0.80
 Glucose, CSF                               | lab    |            605 |     599 |             0.80
 Total Nucleated Cells, Pleural             | lab    |            624 |     581 |             0.78
 Lactate Dehydrogenase, Pleural             | lab    |            612 |     571 |             0.76
 Immunoglobulin M                           | lab    |            585 |     570 |             0.76
 Total Protein, Pleural                     | lab    |            604 |     563 |             0.75
 Total Nucleated Cells, Ascites             | lab    |            563 |     550 |             0.74
 RBC, Pleural                               | lab    |            567 |     530 |             0.71
 Glucose, Pleural                           | lab    |            566 |     530 |             0.71
 RBC, Ascites                               | lab    |            538 |     527 |             0.70
 Gamma Glutamyltransferase                  | lab    |            526 |     508 |             0.68
 Ammonia                                    | lab    |            570 |     504 |             0.67
 Transitional Epithelial Cells              | lab    |            474 |     468 |             0.63
 HPE2                                       | lab    |            481 |     465 |             0.62
 Total Nucleated Cells, Other               | lab    |            456 |     444 |             0.59
 Carboxyhemoglobin                          | lab    |            454 |     422 |             0.56
 Sedimentation Rate                         | lab    |            430 |     421 |             0.56
 Total Protein, Ascites                     | lab    |            409 |     402 |             0.54
 Heparin                                    | lab    |            744 |     396 |             0.53
 Other                                      | lab    |            439 |     395 |             0.53
 Macrophages                                | lab    |            419 |     394 |             0.53
 Triiodothyronine (T3)                      | lab    |            388 |     377 |             0.50
 Methemoglobin                              | lab    |            407 |     362 |             0.48
 C4                                         | lab    |            358 |     352 |             0.47
 Other Cell                                 | lab    |            368 |     343 |             0.46
 STX3                                       | lab    |            391 |     333 |             0.45
 Cholesterol, Pleural                       | lab    |            359 |     328 |             0.44
 Valproic Acid                              | lab    |            433 |     320 |             0.43
 Mesothelial Cell                           | lab    |            322 |     320 |             0.43
 Albumin, Pleural                           | lab    |            349 |     316 |             0.42
 C3                                         | lab    |            320 |     315 |             0.42
 Phosphate, Urine                           | lab    |            318 |     311 |             0.42
 Parathyroid Hormone                        | lab    |            330 |     310 |             0.41
 Mesothelial Cells                          | lab    |            327 |     309 |             0.41
 RBC, Other Fluid                           | lab    |            314 |     300 |             0.40
 Cholesterol, LDL, Measured                 | lab    |            306 |     300 |             0.40
 STX4                                       | lab    |            303 |     295 |             0.39
 STX5                                       | lab    |            301 |     293 |             0.39
 HPE6                                       | lab    |            295 |     290 |             0.39
 Alpha-Fetoprotein                          | lab    |            285 |     280 |             0.37
 Lactate Dehydrogenase, Ascites             | lab    |            277 |     272 |             0.36
 Glucose, Ascites                           | lab    |            277 |     272 |             0.36
 Total Protein, Body Fluid                  | lab    |            267 |     267 |             0.36
 25-OH Vitamin D                            | lab    |            269 |     265 |             0.35
 LD, Body Fluid                             | lab    |            264 |     264 |             0.35
 Glucose, Body Fluid                        | lab    |            261 |     261 |             0.35
 Albumin, Ascites                           | lab    |            257 |     255 |             0.34
 Albumin, Body Fluid                        | lab    |            256 |     256 |             0.34
 HPE4                                       | lab    |            253 |     248 |             0.33
 Blasts                                     | lab    |            325 |     229 |             0.31
 Acetaminophen                              | lab    |            357 |     222 |             0.30
 Other Cells                                | lab    |            309 |     228 |             0.30
 Uric Acid, Urine                           | lab    |            237 |     227 |             0.30
 Calcium, Urine                             | lab    |            233 |     227 |             0.30
 Promyelocytes                              | lab    |            235 |     215 |             0.29
 Carcinoembyronic Antigen (CEA)             | lab    |            217 |     214 |             0.29
 Cyclosporin                                | lab    |            219 |     198 |             0.26
 Rheumatoid Factor                          | lab    |            184 |     180 |             0.24
 N2 GENE CT                                 | lab    |            180 |     178 |             0.24
 E GENE ENDPT                               | lab    |            180 |     178 |             0.24
 E GENE CT                                  | lab    |            180 |     178 |             0.24
 N2 GENE ENDPT                              | lab    |            180 |     178 |             0.24
 CD4/CD8 Ratio                              | lab    |            179 |     176 |             0.24
 WBC Count                                  | lab    |            179 |     176 |             0.24
 Lymphocytes, Percent                       | lab    |            179 |     176 |             0.24
 Amylase, Pleural                           | lab    |            182 |     170 |             0.23
 Absolute CD8 Count                         | lab    |            178 |     175 |             0.23
 Absolute CD4 Count                         | lab    |            178 |     175 |             0.23
 Absolute CD3 Count                         | lab    |            178 |     175 |             0.23
 CD8 Cells, Percent                         | lab    |            178 |     175 |             0.23
 CD4 Cells, Percent                         | lab    |            178 |     175 |             0.23
 CD3 Cells, Percent                         | lab    |            178 |     175 |             0.23
 Magnesium, Urine                           | lab    |            176 |     171 |             0.23
 Beta Hydroxybutyrate                       | lab    |            194 |     163 |             0.22
 Amylase, Ascites                           | lab    |            187 |     167 |             0.22
 proBNP, Pleural                            | lab    |            182 |     163 |             0.22
 Mesothelial cells                          | lab    |            172 |     163 |             0.22
 Hematocrit, Other Fluid                    | lab    |            163 |     162 |             0.22
 Amylase, Body Fluid                        | lab    |            162 |     161 |             0.22
 Phenobarbital                              | lab    |            166 |     150 |             0.20
 Granulocyte Count                          | lab    |            161 |     146 |             0.20
 Bilirubin, Total, Ascites                  | lab    |            159 |     148 |             0.20
 Reticulocyte Count, Manual                 | lab    |            157 |     150 |             0.20
 Free Kappa/Free Lambda Ratio               | lab    |            142 |     142 |             0.19
 Free Lambda                                | lab    |            142 |     142 |             0.19
 Free Kappa                                 | lab    |            141 |     141 |             0.19
 Gentamicin                                 | lab    |            151 |     134 |             0.18
 Albumin/Creatinine, Urine                  | lab    |            134 |     133 |             0.18
 Treponema pallidum (syphilis) value        | lab    |            133 |     133 |             0.18
 Plasma Cells                               | lab    |            137 |     127 |             0.17
 Tobramycin                                 | lab    |            136 |     125 |             0.17
 Lyme G and M Value                         | lab    |            132 |     130 |             0.17
 Albumin, Urine                             | lab    |            131 |     130 |             0.17
 Estimated GFR (CKD- EPI 2021)              | lab    |            126 |     126 |             0.17
 Thrombin                                   | lab    |            130 |     121 |             0.16
 Creatinine, Pleural                        | lab    |            130 |     122 |             0.16
 Epstein-Barr Virus IgM Ab Value            | lab    |            124 |     122 |             0.16
 Prostate Specific Antigen                  | lab    |            122 |     119 |             0.16
 CMV IgG Ab Value                           | lab    |            121 |     121 |             0.16
 Epstein-Barr Virus EBNA IgG Ab             | lab    |            121 |     119 |             0.16
 Epstein-Barr Virus IgG Ab Value            | lab    |            115 |     114 |             0.15
 Lithium                                    | lab    |            218 |     103 |             0.14
 Factor VIII                                | lab    |            126 |     106 |             0.14
 Prolactin                                  | lab    |            108 |     103 |             0.14
 Heparin, LMW                               | lab    |            111 |     100 |             0.13
 Triglycerides, Pleural                     | lab    |            109 |     101 |             0.13
 Creatinine, Ascites                        | lab    |            102 |     100 |             0.13
 STX1                                       | lab    |            135 |      80 |             0.11
 Rapamycin                                  | lab    |             90 |      84 |             0.11
 Ethanol                                    | lab    |             88 |      85 |             0.11
 Protein C, Functional                      | lab    |             86 |      85 |             0.11
 Lactate Dehydrogenase, CSF                 | lab    |             84 |      83 |             0.11
 Protein S, Functional                      | lab    |             83 |      81 |             0.11
 Ceph-IC                                    | lab    |             82 |      81 |             0.11
 COV11                                      | lab    |             80 |      80 |             0.11
 COV10                                      | lab    |             79 |      79 |             0.11
 Hematocrit, Pleural                        | lab    |             91 |      78 |             0.10
 Antithrombin                               | lab    |             83 |      78 |             0.10
 Anticardiolipin Antibody IgM               | lab    |             80 |      78 |             0.10
 Anticardiolipin Antibody IgG               | lab    |             80 |      78 |             0.10
 dRVVT - Screen                             | lab    |             75 |      75 |             0.10
 HPE5                                       | lab    |             75 |      74 |             0.10
 Lining Cell                                | lab    |             73 |      66 |             0.09
 Total Nucleated Cells, Joint               | lab    |             72 |      68 |             0.09
 Tissue Transglutaminase Ab, IgA            | lab    |             71 |      69 |             0.09
 Cellular Cast                              | lab    |             70 |      70 |             0.09
 Hepatitis C Viral Load                     | lab    |             67 |      64 |             0.09
 COV8MC                                     | lab    |             67 |      67 |             0.09
 COV8IC                                     | lab    |             67 |      67 |             0.09
 COV13                                      | lab    |             66 |      66 |             0.09
 COV12                                      | lab    |             66 |      66 |             0.09
 SCT - Screen                               | lab    |             66 |      66 |             0.09
 FLUA1                                      | lab    |             64 |      64 |             0.09
 FLUB2                                      | lab    |             64 |      64 |             0.09
 FLUB1                                      | lab    |             64 |      64 |             0.09
 FLUA2                                      | lab    |             64 |      64 |             0.09
 RSV2                                       | lab    |             64 |      64 |             0.09
 UTX10                                      | lab    |             64 |      64 |             0.09
 RSV1                                       | lab    |             64 |      64 |             0.09
 Bicarbonate, Urine                         | lab    |             62 |      61 |             0.08
 Beta-2 Microglobulin                       | lab    |             61 |      57 |             0.08
 Plasma                                     | lab    |             59 |      54 |             0.07
 RBC, Joint Fluid                           | lab    |             57 |      54 |             0.07
 Quantitative G6PD                          | lab    |             55 |      52 |             0.07
 Calculated TBG                             | lab    |             53 |      51 |             0.07
 Uptake Ratio                               | lab    |             53 |      51 |             0.07
 Calculated Thyroxine (T4) Index            | lab    |             52 |      50 |             0.07
 VZV IgG Ab Value                           | lab    |             51 |      51 |             0.07
 Toxoplasma IgG Ab Value                    | lab    |             50 |      50 |             0.07
 Carbamazepine                              | lab    |             50 |      44 |             0.06
 CephIC Endpt                               | lab    |             49 |      48 |             0.06
 CA-125                                     | lab    |             45 |      45 |             0.06
 Salicylate                                 | lab    |            198 |      40 |             0.05
 Phenytoin, Percent Free                    | lab    |             43 |      40 |             0.05
 Hematocrit, Ascites                        | lab    |             43 |      40 |             0.05
 Phenytoin, Free                            | lab    |             43 |      40 |             0.05
 NRBC                                       | lab    |             42 |      41 |             0.05
 PAN1                                       | lab    |             40 |      35 |             0.05
 STX2                                       | lab    |             40 |      40 |             0.05
 CA 19-9                                    | lab    |             39 |      38 |             0.05
 EE6                                        | lab    |             38 |      37 |             0.05
 RUBIgGV                                    | lab    |             38 |      38 |             0.05
 COV12MC                                    | lab    |             36 |      36 |             0.05
 EE1                                        | lab    |             36 |      36 |             0.05
 COV12IC                                    | lab    |             36 |      36 |             0.05
 Renal Epithelial Cells                     | lab    |             35 |      35 |             0.05
 Mumps IgG Ab Value                         | lab    |             34 |      34 |             0.05
 Von Willebrand Factor Antigen              | lab    |             39 |      31 |             0.04
 Factor VII                                 | lab    |             36 |      33 |             0.04
 EE2                                        | lab    |             34 |      33 |             0.04
 Rubeola IgG Ab Value                       | lab    |             30 |      30 |             0.04
 Length of Urine Collection                 | lab    |             29 |      27 |             0.04
 WBC Casts                                  | lab    |             29 |      29 |             0.04
 Urine Volume                               | lab    |             29 |      27 |             0.04
 Bacteria                                   | lab    |             28 |      28 |             0.04
 Hemogloblin S                              | lab    |             28 |      28 |             0.04
 Hemoglobin C                               | lab    |             28 |      28 |             0.04
 Hemogloblin A                              | lab    |             28 |      28 |             0.04
 Von Willebrand Factor Activity             | lab    |             32 |      26 |             0.03
 Amikacin                                   | lab    |             31 |      26 |             0.03
 Homocysteine                               | lab    |             28 |      26 |             0.03
 Bilirubin, Total, Body Fluid               | lab    |             27 |      24 |             0.03
 dRVVT - Confirmation                       | lab    |             26 |      26 |             0.03
 dRVVT - Normalized Ratio                   | lab    |             26 |      26 |             0.03
 EE7                                        | lab    |             26 |      26 |             0.03
 Serum Viscosity                            | lab    |             24 |      23 |             0.03
 Creatinine, Body Fluid                     | lab    |             23 |      20 |             0.03
 Hemoglobin A2                              | lab    |             23 |      23 |             0.03
 Thyroid Peroxidase Antibodies              | lab    |             21 |      21 |             0.03
 HIV 1 Viral Load                           | lab    |             21 |      21 |             0.03
 Hemoglobin F                               | lab    |             20 |      20 |             0.03
 Broad Casts                                | lab    |             19 |      19 |             0.03
 Follicle Stimulating Hormone               | lab    |             19 |      19 |             0.03
 HPE8                                       | lab    |             19 |      19 |             0.03
 Factor V                                   | lab    |             18 |      18 |             0.02
 Toxoplasma IgM Ab Value                    | lab    |             18 |      18 |             0.02
 24 hr Creatinine                           | lab    |             17 |      17 |             0.02
 Hypersegmented Neutrophils                 | lab    |             17 |      17 |             0.02
 Methotrexate                               | lab    |             17 |      13 |             0.02
 Luteinizing Hormone                        | lab    |             16 |      16 |             0.02
 Factor XI                                  | lab    |             15 |      12 |             0.02
 Waxy Casts                                 | lab    |             15 |      15 |             0.02
 Hematocrit, Joint Fluid                    | lab    |             15 |      15 |             0.02
 Human Chorionic Gonadotropin               | lab    |             14 |      12 |             0.02
 EE5                                        | lab    |             14 |      14 |             0.02
 HBV VL CT                                  | lab    |             14 |      14 |             0.02
 H. pylori IgG Ab Value                     | lab    |             13 |      13 |             0.02
 Bilirubin, Total, Pleural                  | lab    |             13 |      13 |             0.02
 Triglycerides, Ascites                     | lab    |             13 |      13 |             0.02
 RdRP Ct                                    | lab    |             12 |      12 |             0.02
 Factor X                                   | lab    |             12 |      12 |             0.02
 Factor IX                                  | lab    |             12 |      12 |             0.02
 RdRP Endpt                                 | lab    |             12 |      12 |             0.02
 Urine Casts, Other                         | lab    |             12 |      12 |             0.02
 HIT-Ab Numerical Result                    | lab    |             12 |      12 |             0.02
 Ethylene Glycol                            | lab    |             13 |       8 |             0.01
 EE3                                        | lab    |             11 |      11 |             0.01
 Glucose, Urine                             | lab    |             11 |      11 |             0.01
 Cytomegalovirus Viral Load                 | lab    |             10 |      10 |             0.01
 Triglycer                                  | lab    |             10 |      10 |             0.01
 Nucleated RBC                              | lab    |              9 |       9 |             0.01
 24 hr Protein                              | lab    |              9 |       9 |             0.01
 RBC Casts                                  | lab    |              8 |       8 |             0.01
 Factor II                                  | lab    |              8 |       8 |             0.01
 Thyroglobulin                              | lab    |              8 |       8 |             0.01
 wbcp                                       | lab    |              7 |       7 |             0.01
 CD3 %                                      | lab    |              7 |       7 |             0.01
 CD3 Absolute Count                         | lab    |              7 |       7 |             0.01
 Lipase, Ascites                            | lab    |              7 |       6 |             0.01
 Hematocrit, CSF                            | lab    |              7 |       5 |             0.01
 Testosterone                               | lab    |              7 |       7 |             0.01
 Anti-DGP (IgA/IgG)                         | lab    |              6 |       6 |             0.01
 Protein C, Antigen                         | lab    |              6 |       6 |             0.01
 Cancer Antigen 27.29                       | lab    |              6 |       6 |             0.01
 UTX9                                       | lab    |              6 |       6 |             0.01
 Amylase/Creatinine Ratio, Urine            | lab    |              5 |       5 |             0.01
 Protein S, Antigen                         | lab    |              5 |       5 |             0.01
 Reflex Confirmatory Hepatitis C Viral Load | lab    |              5 |       5 |             0.01
 Urea Nitrogen, Body Fluid                  | lab    |              5 |       5 |             0.01
 Theophylline                               | lab    |              5 |       5 |             0.01
 Amylase, Urine                             | lab    |              5 |       5 |             0.01
 High-Sensitivity CRP                       | lab    |              5 |       5 |             0.01
 PAN3                                       | lab    |              5 |       5 |             0.01
 Eosinophil Count                           | lab    |              5 |       5 |             0.01
 CD16/56%                                   | lab    |              4 |       4 |             0.01
 Fetal Hemoglobin                           | lab    |              4 |       4 |             0.01
 Sodium, Body Fluid                         | lab    |              4 |       4 |             0.01
 Sex Hormone Binding Globulin               | lab    |              4 |       4 |             0.01
 Osmolality, Stool                          | lab    |              4 |       4 |             0.01
 HIV Viral Load Ct                          | lab    |              4 |       4 |             0.01
 CD5 %                                      | lab    |              4 |       4 |             0.01
 Potassium, Body Fluid                      | lab    |              4 |       4 |             0.01
 CD5 Absolute Count                         | lab    |              4 |       4 |             0.01
 CD16/56 Absolute Count                     | lab    |              4 |       4 |             0.01
 Young Cells                                | lab    |              3 |       3 |             0.00
 Potassium, Stool                           | lab    |              3 |       3 |             0.00
 Sodium, Stool                              | lab    |              3 |       3 |             0.00
 Hypochromia                                | lab    |              3 |       3 |             0.00
 Hepatitis B Viral Load                     | lab    |              3 |       3 |             0.00
 Hemoglobin Other                           | lab    |              3 |       3 |             0.00
 Cholesterol, Body Fluid                    | lab    |              3 |       3 |             0.00
 Chloride, Stool                            | lab    |              3 |       3 |             0.00
 Bicarbonate, Other Fluid                   | lab    |              3 |       3 |             0.00
 Microcytes                                 | lab    |              2 |       2 |             0.00
 Calculated Free Testosterone               | lab    |              2 |       2 |             0.00
 Cholesterol, Ascites                       | lab    |              2 |       2 |             0.00
 NonSquamous Epithelial Cell                | lab    |              2 |       2 |             0.00
 CD20 Absolute Count                        | lab    |              2 |       2 |             0.00
 HPE9                                       | lab    |              2 |       2 |             0.00
 Bicarbonate, Stool                         | lab    |              2 |       2 |             0.00
 DHEA-Sulfate                               | lab    |              2 |       2 |             0.00
 CD20 %                                     | lab    |              2 |       2 |             0.00
 K (GREEN)                                  | lab    |              2 |       2 |             0.00
 Anti-Thyroglobulin Antibodies              | lab    |              2 |       2 |             0.00
 Osmolality, Body Fluid                     | lab    |              2 |       2 |             0.00
 CD19 Absolute Count                        | lab    |              2 |       2 |             0.00
 PAN2                                       | lab    |              2 |       2 |             0.00
 CD19 %                                     | lab    |              2 |       2 |             0.00
 Lipase, Body Fluid                         | lab    |              2 |       2 |             0.00
 Chloride, Body Fluid                       | lab    |              2 |       2 |             0.00
 Macrocytes                                 | lab    |              2 |       2 |             0.00
 Urine Creatinine                           | lab    |              1 |       1 |             0.00
 Urine Volume, Total                        | lab    |              1 |       1 |             0.00
 CD19                                       | lab    |              1 |       1 |             0.00
 SCT - Confirmation                         | lab    |              1 |       1 |             0.00
 Blood Parasite Smear                       | lab    |              1 |       1 |             0.00
 Non-squamous Epithelial Cells              | lab    |              1 |       1 |             0.00
 Bilirubin, Total, CSF                      | lab    |              1 |       1 |             0.00
 RBC Morphology                             | lab    |              1 |       1 |             0.00
 Bicarbonate, Ascites                       | lab    |              1 |       1 |             0.00
 Basophilic Stippling                       | lab    |              1 |       1 |             0.00
 PAN                                        | lab    |              1 |       1 |             0.00
 Poikilocytosis                             | lab    |              1 |       1 |             0.00
 Factor VIII Inhibitor                      | lab    |              1 |       1 |             0.00
 Total Collection Time                      | lab    |              1 |       1 |             0.00
 Hepatitis B Surface Antibody               | lab    |              1 |       1 |             0.00
 Factor XII                                 | lab    |              1 |       1 |             0.00
 Estradiol                                  | lab    |              1 |       1 |             0.00
 Epstein-Barr Virus Interpretation          | lab    |              1 |       1 |             0.00
 Teardrop Cells                             | lab    |              1 |       1 |             0.00
 Target Cells                               | lab    |              1 |       1 |             0.00
 Howell-Jolly Bodies                        | lab    |              1 |       1 |             0.00
 Creatinine, Serum                          | lab    |              1 |       1 |             0.00
 Creatinine Clearance                       | lab    |              1 |       1 |             0.00
 Polychromasia                              | lab    |              1 |       1 |             0.00
 Spherocytes                                | lab    |              1 |       1 |             0.00
 Potassium, Pleural                         | lab    |              1 |       1 |             0.00
 Leukocyte Alkaline Phosphatase             | lab    |              1 |       1 |             0.00
 Sodium, Pleural                            | lab    |              1 |       1 |             0.00
 Sickle Cells                               | lab    |              1 |       1 |             0.00
 CD34                                       | lab    |              1 |       1 |             0.00
 Lipase, Pleural                            | lab    |              1 |       1 |             0.00
 CD3                                        | lab    |              1 |       1 |             0.00
 SCT - Normalized Ratio                     | lab    |              1 |       1 |             0.00
(473 rows)


*/
