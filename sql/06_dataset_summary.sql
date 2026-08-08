-- # dataset_summary.sql
-- 1. Dataset Summary
SELECT COUNT(*) 
FROM mimiciv_derived.trajectory_first24h;
--  19562032

SELECT COUNT(DISTINCT stay_id)
FROM mimiciv_derived.trajectory_first24h;
--  74829

SELECT COUNT(DISTINCT label)
FROM mimiciv_derived.trajectory_first24h;
--    473

-- 2. Top Clinical Variables
SELECT
    label,
    COUNT(*) AS n
FROM mimiciv_derived.trajectory_first24h
GROUP BY label
ORDER BY n DESC;

-- 3. Patients per Variable

SELECT
    label,
    COUNT(*) AS n_measurements,
    COUNT(DISTINCT stay_id) AS n_stays
FROM mimiciv_derived.trajectory_first24h
GROUP BY label
ORDER BY n_measurements DESC;

-- 4. Measurement Frequency

SELECT
    source,
    COUNT(*) AS n_measurements
FROM mimiciv_derived.trajectory_first24h
GROUP BY source
ORDER BY n_measurements DESC;
/*
 source | n_measurements 
--------+----------------
 vital  |       13,016,626
 lab    |        6,545,406
 */



/*
2. Top Clinical Variables
                   label                    |    n    
--------------------------------------------+---------
 Heart Rate                                 | 2096007
 Respiratory Rate                           | 2071233
 O2 saturation pulseoxymetry                | 2052876
 Non Invasive Blood Pressure systolic       | 1345335
 Non Invasive Blood Pressure diastolic      | 1345047
 Non Invasive Blood Pressure mean           | 1344022
 Arterial Blood Pressure mean               |  723725
 Arterial Blood Pressure systolic           |  720624
 Arterial Blood Pressure diastolic          |  720514
 Temperature Fahrenheit                     |  467790
 Glucose                                    |  243415
 pH                                         |  216980
 Hemoglobin                                 |  207276
 pO2                                        |  187275
 Base Excess                                |  187084
 pCO2                                       |  187080
 Calculated Total CO2                       |  187077
 Hematocrit                                 |  184319
 Potassium                                  |  166091
 Chloride                                   |  165555
 Platelet Count                             |  162552
 Sodium                                     |  162520
 Creatinine                                 |  160101
 Urea Nitrogen                              |  159639
 White Blood Cells                          |  159414
 Bicarbonate                                |  159294
 MCHC                                       |  159242
 Red Blood Cells                            |  159239
 MCV                                        |  159235
 MCH                                        |  159197
 RDW                                        |  159096
 Anion Gap                                  |  157789
 Magnesium                                  |  146571
 Phosphate                                  |  138419
 Calcium, Total                             |  137319
 Lactate                                    |  132547
 Temperature Celsius                        |  129453
 PTT                                        |  123793
 PT                                         |  119839
 INR(PT)                                    |  119802
 Free Calcium                               |  102413
 H                                          |   93760
 L                                          |   93759
 I                                          |   93758
 RDW-SD                                     |   91385
 Potassium, Whole Blood                     |   81352
 Oxygen Saturation                          |   64266
 Asparate Aminotransferase (AST)            |   50218
 Alanine Aminotransferase (ALT)             |   49770
 Bilirubin, Total                           |   49734
 Alkaline Phosphatase                       |   49376
 Hematocrit, Calculated                     |   45174
 Sodium, Whole Blood                        |   42685
 Lymphocytes                                |   33356
 Creatine Kinase, MB Isoenzyme              |   32835
 Monocytes                                  |   32560
 Eosinophils                                |   31654
 Basophils                                  |   31200
 Neutrophils                                |   31067
 Creatine Kinase (CK)                       |   30334
 Troponin T                                 |   29378
 Fibrinogen, Functional                     |   28806
 Lactate Dehydrogenase (LD)                 |   28710
 Albumin                                    |   27215
 Temperature                                |   26013
 Chloride, Whole Blood                      |   24215
 Oxygen                                     |   18170
 Absolute Lymphocyte Count                  |   17651
 Absolute Neutrophil Count                  |   17475
 Absolute Eosinophil Count                  |   17475
 Absolute Monocyte Count                    |   17473
 Absolute Basophil Count                    |   17473
 Specific Gravity                           |   17079
 PEEP                                       |   15680
 Immature Granulocytes                      |   13076
 Tidal Volume                               |   13027
 WBC                                        |   11423
 RBC                                        |   11098
 Epithelial Cells                           |   10467
 Protein                                    |   10108
 CK-MB Index                                |    8394
 Bands                                      |    7906
 Creatinine, Urine                          |    7283
 Metamyelocytes                             |    7095
 Thyroid Stimulating Hormone                |    7078
 Myelocytes                                 |    6922
 Triglycerides                              |    6818
 Atypical Lymphocytes                       |    6759
 Osmolality, Urine                          |    6486
 Lipase                                     |    6465
 Sodium, Urine                              |    6347
 Osmolality, Measured                       |    6273
 % Hemoglobin A1c                           |    5557
 eAG                                        |    5255
 Hyaline Casts                              |    4875
 Amylase                                    |    4874
 Cholesterol, Total                         |    4575
 Urea Nitrogen, Urine                       |    4542
 Potassium, Urine                           |    4512
 Cholesterol, HDL                           |    4466
 Cholesterol Ratio (Total/HDL)              |    4423
 Required O2                                |    4257
 Vancomycin                                 |    4257
 Alveolar-arterial Gradient                 |    4251
 Cholesterol, LDL, Calculated               |    4242
 Bilirubin, Direct                          |    4206
 Bilirubin, Indirect                        |    3973
 Ferritin                                   |    3927
 Chloride, Urine                            |    3788
 Nucleated Red Cells                        |    3497
 Iron                                       |    3350
 Haptoglobin                                |    3300
 Transferrin                                |    3162
 Polys                                      |    3149
 Iron Binding Capacity, Total               |    3147
 Ketone                                     |    3045
 Urobilinogen                               |    2743
 NTproBNP                                   |    2608
 Cortisol                                   |    2482
 Reticulocyte Count, Automated              |    2475
 O2 Flow                                    |    2425
 C-Reactive Protein                         |    2127
 Uric Acid                                  |    2125
 Calculated Bicarbonate, Whole Blood        |    2021
 Phenytoin                                  |    1905
 Reticulocyte Count, Absolute               |    1709
 Monos                                      |    1656
 HPE1                                       |    1602
 HPE7                                       |    1501
 Vitamin B12                                |    1463
 HPE3                                       |    1412
 Protein, Total                             |    1398
 Macrophage                                 |    1342
 Granular Casts                             |    1291
 D-Dimer                                    |    1273
 Thyroxine (T4), Free                       |    1165
 Creatinine, Whole Blood                    |    1135
 tacroFK                                    |    1094
 UTX4                                       |    1090
 UTX5                                       |    1089
 UTX2                                       |    1082
 UTX1                                       |    1077
 UTX7                                       |    1071
 UTX3                                       |    1069
 UTX6                                       |    1024
 ARCH-1                                     |     898
 Total Protein, Urine                       |     870
 Estimated GFR (CKD- EPI Refit)             |     863
 Lymphs                                     |     860
 Total Nucleated Cells, CSF                 |     859
 RBC, CSF                                   |     853
 Heparin                                    |     744
 Immunoglobulin G                           |     742
 Protein/Creatinine Ratio                   |     740
 Folate                                     |     732
 STX6                                       |     727
 Globulin                                   |     722
 Digoxin                                    |     708
 Thyroxine (T4)                             |     662
 Immunoglobulin A                           |     632
 Total Nucleated Cells, Pleural             |     624
 Lactate Dehydrogenase, Pleural             |     612
 Total Protein, CSF                         |     605
 Glucose, CSF                               |     605
 Total Protein, Pleural                     |     604
 Immunoglobulin M                           |     585
 Ammonia                                    |     570
 RBC, Pleural                               |     567
 Glucose, Pleural                           |     566
 Total Nucleated Cells, Ascites             |     563
 RBC, Ascites                               |     538
 Gamma Glutamyltransferase                  |     526
 HPE2                                       |     481
 Transitional Epithelial Cells              |     474
 Total Nucleated Cells, Other               |     456
 Carboxyhemoglobin                          |     454
 Other                                      |     439
 Valproic Acid                              |     433
 Sedimentation Rate                         |     430
 Macrophages                                |     419
 Total Protein, Ascites                     |     409
 Methemoglobin                              |     407
 STX3                                       |     391
 Triiodothyronine (T3)                      |     388
 Other Cell                                 |     368
 Cholesterol, Pleural                       |     359
 C4                                         |     358
 Acetaminophen                              |     357
 Albumin, Pleural                           |     349
 Parathyroid Hormone                        |     330
 Mesothelial Cells                          |     327
 Blasts                                     |     325
 Mesothelial Cell                           |     322
 C3                                         |     320
 Phosphate, Urine                           |     318
 RBC, Other Fluid                           |     314
 Other Cells                                |     309
 Cholesterol, LDL, Measured                 |     306
 STX4                                       |     303
 STX5                                       |     301
 HPE6                                       |     295
 Alpha-Fetoprotein                          |     285
 Glucose, Ascites                           |     277
 Lactate Dehydrogenase, Ascites             |     277
 25-OH Vitamin D                            |     269
 Total Protein, Body Fluid                  |     267
 LD, Body Fluid                             |     264
 Glucose, Body Fluid                        |     261
 Albumin, Ascites                           |     257
 Albumin, Body Fluid                        |     256
 HPE4                                       |     253
 Uric Acid, Urine                           |     237
 Promyelocytes                              |     235
 Calcium, Urine                             |     233
 Cyclosporin                                |     219
 Lithium                                    |     218
 Carcinoembyronic Antigen (CEA)             |     217
 Salicylate                                 |     198
 Beta Hydroxybutyrate                       |     194
 Amylase, Ascites                           |     187
 Rheumatoid Factor                          |     184
 Amylase, Pleural                           |     182
 proBNP, Pleural                            |     182
 N2 GENE ENDPT                              |     180
 E GENE ENDPT                               |     180
 E GENE CT                                  |     180
 N2 GENE CT                                 |     180
 Lymphocytes, Percent                       |     179
 CD4/CD8 Ratio                              |     179
 WBC Count                                  |     179
 Absolute CD3 Count                         |     178
 Absolute CD4 Count                         |     178
 CD3 Cells, Percent                         |     178
 CD8 Cells, Percent                         |     178
 Absolute CD8 Count                         |     178
 CD4 Cells, Percent                         |     178
 Magnesium, Urine                           |     176
 Mesothelial cells                          |     172
 Phenobarbital                              |     166
 Hematocrit, Other Fluid                    |     163
 Amylase, Body Fluid                        |     162
 Granulocyte Count                          |     161
 Bilirubin, Total, Ascites                  |     159
 Reticulocyte Count, Manual                 |     157
 Gentamicin                                 |     151
 Free Kappa/Free Lambda Ratio               |     142
 Free Lambda                                |     142
 Free Kappa                                 |     141
 Plasma Cells                               |     137
 Tobramycin                                 |     136
 STX1                                       |     135
 Albumin/Creatinine, Urine                  |     134
 Treponema pallidum (syphilis) value        |     133
 Lyme G and M Value                         |     132
 Albumin, Urine                             |     131
 Creatinine, Pleural                        |     130
 Thrombin                                   |     130
 Factor VIII                                |     126
 Estimated GFR (CKD- EPI 2021)              |     126
 Epstein-Barr Virus IgM Ab Value            |     124
 Prostate Specific Antigen                  |     122
 CMV IgG Ab Value                           |     121
 Epstein-Barr Virus EBNA IgG Ab             |     121
 Epstein-Barr Virus IgG Ab Value            |     115
 Heparin, LMW                               |     111
 Triglycerides, Pleural                     |     109
 Prolactin                                  |     108
 Creatinine, Ascites                        |     102
 Hematocrit, Pleural                        |      91
 Rapamycin                                  |      90
 Ethanol                                    |      88
 Protein C, Functional                      |      86
 Lactate Dehydrogenase, CSF                 |      84
 Protein S, Functional                      |      83
 Antithrombin                               |      83
 Ceph-IC                                    |      82
 Anticardiolipin Antibody IgG               |      80
 Anticardiolipin Antibody IgM               |      80
 COV11                                      |      80
 COV10                                      |      79
 HPE5                                       |      75
 dRVVT - Screen                             |      75
 Lining Cell                                |      73
 Total Nucleated Cells, Joint               |      72
 Tissue Transglutaminase Ab, IgA            |      71
 Cellular Cast                              |      70
 COV8MC                                     |      67
 COV8IC                                     |      67
 Hepatitis C Viral Load                     |      67
 COV12                                      |      66
 COV13                                      |      66
 SCT - Screen                               |      66
 FLUA1                                      |      64
 UTX10                                      |      64
 RSV2                                       |      64
 FLUB2                                      |      64
 RSV1                                       |      64
 FLUA2                                      |      64
 FLUB1                                      |      64
 Bicarbonate, Urine                         |      62
 Beta-2 Microglobulin                       |      61
 Plasma                                     |      59
 RBC, Joint Fluid                           |      57
 Quantitative G6PD                          |      55
 Uptake Ratio                               |      53
 Calculated TBG                             |      53
 Calculated Thyroxine (T4) Index            |      52
 VZV IgG Ab Value                           |      51
 Toxoplasma IgG Ab Value                    |      50
 Carbamazepine                              |      50
 CephIC Endpt                               |      49
 CA-125                                     |      45
 Phenytoin, Percent Free                    |      43
 Hematocrit, Ascites                        |      43
 Phenytoin, Free                            |      43
 NRBC                                       |      42
 STX2                                       |      40
 PAN1                                       |      40
 Von Willebrand Factor Antigen              |      39
 CA 19-9                                    |      39
 EE6                                        |      38
 RUBIgGV                                    |      38
 Factor VII                                 |      36
 COV12IC                                    |      36
 COV12MC                                    |      36
 EE1                                        |      36
 Renal Epithelial Cells                     |      35
 EE2                                        |      34
 Mumps IgG Ab Value                         |      34
 Von Willebrand Factor Activity             |      32
 Amikacin                                   |      31
 Rubeola IgG Ab Value                       |      30
 Length of Urine Collection                 |      29
 Urine Volume                               |      29
 WBC Casts                                  |      29
 Homocysteine                               |      28
 Hemoglobin C                               |      28
 Hemogloblin A                              |      28
 Hemogloblin S                              |      28
 Bacteria                                   |      28
 Bilirubin, Total, Body Fluid               |      27
 EE7                                        |      26
 dRVVT - Confirmation                       |      26
 dRVVT - Normalized Ratio                   |      26
 Serum Viscosity                            |      24
 Hemoglobin A2                              |      23
 Creatinine, Body Fluid                     |      23
 Thyroid Peroxidase Antibodies              |      21
 HIV 1 Viral Load                           |      21
 Hemoglobin F                               |      20
 Broad Casts                                |      19
 HPE8                                       |      19
 Follicle Stimulating Hormone               |      19
 Factor V                                   |      18
 Toxoplasma IgM Ab Value                    |      18
 24 hr Creatinine                           |      17
 Hypersegmented Neutrophils                 |      17
 Methotrexate                               |      17
 Luteinizing Hormone                        |      16
 Waxy Casts                                 |      15
 Hematocrit, Joint Fluid                    |      15
 Factor XI                                  |      15
 Human Chorionic Gonadotropin               |      14
 EE5                                        |      14
 HBV VL CT                                  |      14
 H. pylori IgG Ab Value                     |      13
 Ethylene Glycol                            |      13
 Bilirubin, Total, Pleural                  |      13
 Triglycerides, Ascites                     |      13
 RdRP Ct                                    |      12
 Factor X                                   |      12
 Factor IX                                  |      12
 RdRP Endpt                                 |      12
 Urine Casts, Other                         |      12
 HIT-Ab Numerical Result                    |      12
 EE3                                        |      11
 Glucose, Urine                             |      11
 Cytomegalovirus Viral Load                 |      10
 Triglycer                                  |      10
 Nucleated RBC                              |       9
 24 hr Protein                              |       9
 RBC Casts                                  |       8
 Factor II                                  |       8
 Thyroglobulin                              |       8
 wbcp                                       |       7
 CD3 %                                      |       7
 CD3 Absolute Count                         |       7
 Lipase, Ascites                            |       7
 Hematocrit, CSF                            |       7
 Testosterone                               |       7
 Anti-DGP (IgA/IgG)                         |       6
 Protein C, Antigen                         |       6
 Cancer Antigen 27.29                       |       6
 UTX9                                       |       6
 Amylase/Creatinine Ratio, Urine            |       5
 Protein S, Antigen                         |       5
 Reflex Confirmatory Hepatitis C Viral Load |       5
 Urea Nitrogen, Body Fluid                  |       5
 Theophylline                               |       5
 Amylase, Urine                             |       5
 High-Sensitivity CRP                       |       5
 PAN3                                       |       5
 Eosinophil Count                           |       5
 CD16/56%                                   |       4
 Fetal Hemoglobin                           |       4
 Sodium, Body Fluid                         |       4
 Sex Hormone Binding Globulin               |       4
 Osmolality, Stool                          |       4
 HIV Viral Load Ct                          |       4
 CD5 %                                      |       4
 Potassium, Body Fluid                      |       4
 CD5 Absolute Count                         |       4
 CD16/56 Absolute Count                     |       4
 Young Cells                                |       3
 Potassium, Stool                           |       3
 Sodium, Stool                              |       3
 Hypochromia                                |       3
 Hepatitis B Viral Load                     |       3
 Hemoglobin Other                           |       3
 Cholesterol, Body Fluid                    |       3
 Chloride, Stool                            |       3
 Bicarbonate, Other Fluid                   |       3
 Microcytes                                 |       2
 Calculated Free Testosterone               |       2
 Cholesterol, Ascites                       |       2
 NonSquamous Epithelial Cell                |       2
 CD20 Absolute Count                        |       2
 HPE9                                       |       2
 Bicarbonate, Stool                         |       2
 DHEA-Sulfate                               |       2
 CD20 %                                     |       2
 K (GREEN)                                  |       2
 Anti-Thyroglobulin Antibodies              |       2
 Osmolality, Body Fluid                     |       2
 CD19 Absolute Count                        |       2
 PAN2                                       |       2
 CD19 %                                     |       2
 Lipase, Body Fluid                         |       2
 Chloride, Body Fluid                       |       2
 Macrocytes                                 |       2
 Urine Creatinine                           |       1
 Urine Volume, Total                        |       1
 CD19                                       |       1
 SCT - Confirmation                         |       1
 Blood Parasite Smear                       |       1
 Non-squamous Epithelial Cells              |       1
 Bilirubin, Total, CSF                      |       1
 RBC Morphology                             |       1
 Bicarbonate, Ascites                       |       1
 Basophilic Stippling                       |       1
 PAN                                        |       1
 Poikilocytosis                             |       1
 Factor VIII Inhibitor                      |       1
 Total Collection Time                      |       1
 Hepatitis B Surface Antibody               |       1
 Factor XII                                 |       1
 Estradiol                                  |       1
 Epstein-Barr Virus Interpretation          |       1
 Teardrop Cells                             |       1
 Target Cells                               |       1
 Howell-Jolly Bodies                        |       1
 Creatinine, Serum                          |       1
 Creatinine Clearance                       |       1
 Polychromasia                              |       1
 Spherocytes                                |       1
 Potassium, Pleural                         |       1
 Leukocyte Alkaline Phosphatase             |       1
 Sodium, Pleural                            |       1
 Sickle Cells                               |       1
 CD34                                       |       1
 Lipase, Pleural                            |       1
 CD3                                        |       1
 SCT - Normalized Ratio                     |       1
(473 rows)

*/


/*

                   label                    | n_measurements | n_stays 
--------------------------------------------+----------------+---------
 Heart Rate                                 |        2096007 |   74752
 Respiratory Rate                           |        2071233 |   74615
 O2 saturation pulseoxymetry                |        2052876 |   74731
 Non Invasive Blood Pressure systolic       |        1345335 |   67425
 Non Invasive Blood Pressure diastolic      |        1345047 |   67415
 Non Invasive Blood Pressure mean           |        1344022 |   67434
 Arterial Blood Pressure mean               |         723725 |   29412
 Arterial Blood Pressure systolic           |         720624 |   29191
 Arterial Blood Pressure diastolic          |         720514 |   29199
 Temperature Fahrenheit                     |         467790 |   69629
 Glucose                                    |         243415 |   73659
 pH                                         |         216980 |   52021
 Hemoglobin                                 |         207276 |   73301
 pO2                                        |         187275 |   44985
 Base Excess                                |         187084 |   44985
 pCO2                                       |         187080 |   44979
 Calculated Total CO2                       |         187077 |   44979
 Hematocrit                                 |         184319 |   73381
 Potassium                                  |         166091 |   73606
 Chloride                                   |         165555 |   73648
 Platelet Count                             |         162552 |   73274
 Sodium                                     |         162520 |   73645
 Creatinine                                 |         160101 |   73629
 Urea Nitrogen                              |         159639 |   73616
 White Blood Cells                          |         159414 |   73269
 Bicarbonate                                |         159294 |   73617
 MCHC                                       |         159242 |   73248
 Red Blood Cells                            |         159239 |   73256
 MCV                                        |         159235 |   73255
 MCH                                        |         159197 |   73245
 RDW                                        |         159096 |   73210
 Anion Gap                                  |         157789 |   73545
 Magnesium                                  |         146571 |   71301
 Phosphate                                  |         138419 |   68588
 Calcium, Total                             |         137319 |   67981
 Lactate                                    |         132547 |   44183
 Temperature Celsius                        |         129453 |    7064
 PTT                                        |         123793 |   62512
 PT                                         |         119839 |   63030
 INR(PT)                                    |         119802 |   63027
 Free Calcium                               |         102413 |   30527
 H                                          |          93760 |   34749
 L                                          |          93759 |   34748
 I                                          |          93758 |   34748
 RDW-SD                                     |          91385 |   39736
 Potassium, Whole Blood                     |          81352 |   21436
 Oxygen Saturation                          |          64266 |   21244
 Asparate Aminotransferase (AST)            |          50218 |   34311
 Alanine Aminotransferase (ALT)             |          49770 |   33996
 Bilirubin, Total                           |          49734 |   33820
 Alkaline Phosphatase                       |          49376 |   33900
 Hematocrit, Calculated                     |          45174 |   16229
 Sodium, Whole Blood                        |          42685 |   17127
 Lymphocytes                                |          33356 |   28168
 Creatine Kinase, MB Isoenzyme              |          32835 |   18278
 Monocytes                                  |          32560 |   27763
 Eosinophils                                |          31654 |   27372
 Basophils                                  |          31200 |   27137
 Neutrophils                                |          31067 |   27058
 Creatine Kinase (CK)                       |          30334 |   18224
 Troponin T                                 |          29378 |   14919
 Fibrinogen, Functional                     |          28806 |   17925
 Lactate Dehydrogenase (LD)                 |          28710 |   21514
 Albumin                                    |          27215 |   21310
 Temperature                                |          26013 |   13655
 Chloride, Whole Blood                      |          24215 |   14847
 Oxygen                                     |          18170 |   10364
 Absolute Lymphocyte Count                  |          17651 |   15461
 Absolute Neutrophil Count                  |          17475 |   15371
 Absolute Eosinophil Count                  |          17475 |   15373
 Absolute Monocyte Count                    |          17473 |   15371
 Absolute Basophil Count                    |          17473 |   15371
 Specific Gravity                           |          17079 |   15782
 PEEP                                       |          15680 |    8723
 Immature Granulocytes                      |          13076 |   11945
 Tidal Volume                               |          13027 |    7387
 WBC                                        |          11423 |   10932
 RBC                                        |          11098 |   10651
 Epithelial Cells                           |          10467 |   10040
 Protein                                    |          10108 |    9573
 CK-MB Index                                |           8394 |    4595
 Bands                                      |           7906 |    6555
 Creatinine, Urine                          |           7283 |    6720
 Metamyelocytes                             |           7095 |    5893
 Thyroid Stimulating Hormone                |           7078 |    6897
 Myelocytes                                 |           6922 |    5753
 Triglycerides                              |           6818 |    6329
 Atypical Lymphocytes                       |           6759 |    5620
 Osmolality, Urine                          |           6486 |    5419
 Lipase                                     |           6465 |    5481
 Sodium, Urine                              |           6347 |    5700
 Osmolality, Measured                       |           6273 |    3422
 % Hemoglobin A1c                           |           5557 |    5438
 eAG                                        |           5255 |    5140
 Hyaline Casts                              |           4875 |    4755
 Amylase                                    |           4874 |    4076
 Cholesterol, Total                         |           4575 |    4453
 Urea Nitrogen, Urine                       |           4542 |    4343
 Potassium, Urine                           |           4512 |    4030
 Cholesterol, HDL                           |           4466 |    4356
 Cholesterol Ratio (Total/HDL)              |           4423 |    4320
 Required O2                                |           4257 |    2893
 Vancomycin                                 |           4257 |    3909
 Alveolar-arterial Gradient                 |           4251 |    2891
 Cholesterol, LDL, Calculated               |           4242 |    4149
 Bilirubin, Direct                          |           4206 |    2649
 Bilirubin, Indirect                        |           3973 |    2462
 Ferritin                                   |           3927 |    3705
 Chloride, Urine                            |           3788 |    3410
 Nucleated Red Cells                        |           3497 |    2978
 Iron                                       |           3350 |    3226
 Haptoglobin                                |           3300 |    2942
 Transferrin                                |           3162 |    3073
 Polys                                      |           3149 |    2685
 Iron Binding Capacity, Total               |           3147 |    3060
 Ketone                                     |           3045 |    2895
 Urobilinogen                               |           2743 |    2662
 NTproBNP                                   |           2608 |    2530
 Cortisol                                   |           2482 |    2010
 Reticulocyte Count, Automated              |           2475 |    2341
 O2 Flow                                    |           2425 |    2078
 C-Reactive Protein                         |           2127 |    1974
 Uric Acid                                  |           2125 |    1216
 Calculated Bicarbonate, Whole Blood        |           2021 |    1561
 Phenytoin                                  |           1905 |    1433
 Reticulocyte Count, Absolute               |           1709 |    1608
 Monos                                      |           1656 |    1501
 HPE1                                       |           1602 |    1552
 HPE7                                       |           1501 |    1456
 Vitamin B12                                |           1463 |    1442
 HPE3                                       |           1412 |    1371
 Protein, Total                             |           1398 |    1334
 Macrophage                                 |           1342 |    1217
 Granular Casts                             |           1291 |    1266
 D-Dimer                                    |           1273 |    1061
 Thyroxine (T4), Free                       |           1165 |    1144
 Creatinine, Whole Blood                    |           1135 |     809
 tacroFK                                    |           1094 |     979
 UTX4                                       |           1090 |    1084
 UTX5                                       |           1089 |    1083
 UTX2                                       |           1082 |    1076
 UTX1                                       |           1077 |    1071
 UTX7                                       |           1071 |    1065
 UTX3                                       |           1069 |    1061
 UTX6                                       |           1024 |    1018
 ARCH-1                                     |            898 |     884
 Total Protein, Urine                       |            870 |     846
 Estimated GFR (CKD- EPI Refit)             |            863 |     698
 Lymphs                                     |            860 |     611
 Total Nucleated Cells, CSF                 |            859 |     612
 RBC, CSF                                   |            853 |     609
 Heparin                                    |            744 |     396
 Immunoglobulin G                           |            742 |     721
 Protein/Creatinine Ratio                   |            740 |     722
 Folate                                     |            732 |     723
 STX6                                       |            727 |     707
 Globulin                                   |            722 |     702
 Digoxin                                    |            708 |     644
 Thyroxine (T4)                             |            662 |     645
 Immunoglobulin A                           |            632 |     613
 Total Nucleated Cells, Pleural             |            624 |     581
 Lactate Dehydrogenase, Pleural             |            612 |     571
 Total Protein, CSF                         |            605 |     599
 Glucose, CSF                               |            605 |     599
 Total Protein, Pleural                     |            604 |     563
 Immunoglobulin M                           |            585 |     570
 Ammonia                                    |            570 |     504
 RBC, Pleural                               |            567 |     530
 Glucose, Pleural                           |            566 |     530
 Total Nucleated Cells, Ascites             |            563 |     550
 RBC, Ascites                               |            538 |     527
 Gamma Glutamyltransferase                  |            526 |     508
 HPE2                                       |            481 |     465
 Transitional Epithelial Cells              |            474 |     468
 Total Nucleated Cells, Other               |            456 |     444
 Carboxyhemoglobin                          |            454 |     422
 Other                                      |            439 |     395
 Valproic Acid                              |            433 |     320
 Sedimentation Rate                         |            430 |     421
 Macrophages                                |            419 |     394
 Total Protein, Ascites                     |            409 |     402
 Methemoglobin                              |            407 |     362
 STX3                                       |            391 |     333
 Triiodothyronine (T3)                      |            388 |     377
 Other Cell                                 |            368 |     343
 Cholesterol, Pleural                       |            359 |     328
 C4                                         |            358 |     352
 Acetaminophen                              |            357 |     222
 Albumin, Pleural                           |            349 |     316
 Parathyroid Hormone                        |            330 |     310
 Mesothelial Cells                          |            327 |     309
 Blasts                                     |            325 |     229
 Mesothelial Cell                           |            322 |     320
 C3                                         |            320 |     315
 Phosphate, Urine                           |            318 |     311
 RBC, Other Fluid                           |            314 |     300
 Other Cells                                |            309 |     228
 Cholesterol, LDL, Measured                 |            306 |     300
 STX4                                       |            303 |     295
 STX5                                       |            301 |     293
 HPE6                                       |            295 |     290
 Alpha-Fetoprotein                          |            285 |     280
 Glucose, Ascites                           |            277 |     272
 Lactate Dehydrogenase, Ascites             |            277 |     272
 25-OH Vitamin D                            |            269 |     265
 Total Protein, Body Fluid                  |            267 |     267
 LD, Body Fluid                             |            264 |     264
 Glucose, Body Fluid                        |            261 |     261
 Albumin, Ascites                           |            257 |     255
 Albumin, Body Fluid                        |            256 |     256
 HPE4                                       |            253 |     248
 Uric Acid, Urine                           |            237 |     227
 Promyelocytes                              |            235 |     215
 Calcium, Urine                             |            233 |     227
 Cyclosporin                                |            219 |     198
 Lithium                                    |            218 |     103
 Carcinoembyronic Antigen (CEA)             |            217 |     214
 Salicylate                                 |            198 |      40
 Beta Hydroxybutyrate                       |            194 |     163
 Amylase, Ascites                           |            187 |     167
 Rheumatoid Factor                          |            184 |     180
 Amylase, Pleural                           |            182 |     170
 proBNP, Pleural                            |            182 |     163
 N2 GENE ENDPT                              |            180 |     178
 E GENE ENDPT                               |            180 |     178
 E GENE CT                                  |            180 |     178
 N2 GENE CT                                 |            180 |     178
 Lymphocytes, Percent                       |            179 |     176
 CD4/CD8 Ratio                              |            179 |     176
 WBC Count                                  |            179 |     176
 Absolute CD3 Count                         |            178 |     175
 Absolute CD4 Count                         |            178 |     175
 CD3 Cells, Percent                         |            178 |     175
 CD8 Cells, Percent                         |            178 |     175
 Absolute CD8 Count                         |            178 |     175
 CD4 Cells, Percent                         |            178 |     175
 Magnesium, Urine                           |            176 |     171
 Mesothelial cells                          |            172 |     163
 Phenobarbital                              |            166 |     150
 Hematocrit, Other Fluid                    |            163 |     162
 Amylase, Body Fluid                        |            162 |     161
 Granulocyte Count                          |            161 |     146
 Bilirubin, Total, Ascites                  |            159 |     148
 Reticulocyte Count, Manual                 |            157 |     150
 Gentamicin                                 |            151 |     134
 Free Kappa/Free Lambda Ratio               |            142 |     142
 Free Lambda                                |            142 |     142
 Free Kappa                                 |            141 |     141
 Plasma Cells                               |            137 |     127
 Tobramycin                                 |            136 |     125
 STX1                                       |            135 |      80
 Albumin/Creatinine, Urine                  |            134 |     133
 Treponema pallidum (syphilis) value        |            133 |     133
 Lyme G and M Value                         |            132 |     130
 Albumin, Urine                             |            131 |     130
 Creatinine, Pleural                        |            130 |     122
 Thrombin                                   |            130 |     121
 Factor VIII                                |            126 |     106
 Estimated GFR (CKD- EPI 2021)              |            126 |     126
 Epstein-Barr Virus IgM Ab Value            |            124 |     122
 Prostate Specific Antigen                  |            122 |     119
 CMV IgG Ab Value                           |            121 |     121
 Epstein-Barr Virus EBNA IgG Ab             |            121 |     119
 Epstein-Barr Virus IgG Ab Value            |            115 |     114
 Heparin, LMW                               |            111 |     100
 Triglycerides, Pleural                     |            109 |     101
 Prolactin                                  |            108 |     103
 Creatinine, Ascites                        |            102 |     100
 Hematocrit, Pleural                        |             91 |      78
 Rapamycin                                  |             90 |      84
 Ethanol                                    |             88 |      85
 Protein C, Functional                      |             86 |      85
 Lactate Dehydrogenase, CSF                 |             84 |      83
 Protein S, Functional                      |             83 |      81
 Antithrombin                               |             83 |      78
 Ceph-IC                                    |             82 |      81
 Anticardiolipin Antibody IgG               |             80 |      78
 Anticardiolipin Antibody IgM               |             80 |      78
 COV11                                      |             80 |      80
 COV10                                      |             79 |      79
 HPE5                                       |             75 |      74
 dRVVT - Screen                             |             75 |      75
 Lining Cell                                |             73 |      66
 Total Nucleated Cells, Joint               |             72 |      68
 Tissue Transglutaminase Ab, IgA            |             71 |      69
 Cellular Cast                              |             70 |      70
 COV8MC                                     |             67 |      67
 COV8IC                                     |             67 |      67
 Hepatitis C Viral Load                     |             67 |      64
 COV12                                      |             66 |      66
 COV13                                      |             66 |      66
 SCT - Screen                               |             66 |      66
 FLUA1                                      |             64 |      64
 UTX10                                      |             64 |      64
 RSV2                                       |             64 |      64
 FLUB2                                      |             64 |      64
 RSV1                                       |             64 |      64
 FLUA2                                      |             64 |      64
 FLUB1                                      |             64 |      64
 Bicarbonate, Urine                         |             62 |      61
 Beta-2 Microglobulin                       |             61 |      57
 Plasma                                     |             59 |      54
 RBC, Joint Fluid                           |             57 |      54
 Quantitative G6PD                          |             55 |      52
 Uptake Ratio                               |             53 |      51
 Calculated TBG                             |             53 |      51
 Calculated Thyroxine (T4) Index            |             52 |      50
 VZV IgG Ab Value                           |             51 |      51
 Toxoplasma IgG Ab Value                    |             50 |      50
 Carbamazepine                              |             50 |      44
 CephIC Endpt                               |             49 |      48
 CA-125                                     |             45 |      45
 Phenytoin, Percent Free                    |             43 |      40
 Hematocrit, Ascites                        |             43 |      40
 Phenytoin, Free                            |             43 |      40
 NRBC                                       |             42 |      41
 STX2                                       |             40 |      40
 PAN1                                       |             40 |      35
 Von Willebrand Factor Antigen              |             39 |      31
 CA 19-9                                    |             39 |      38
 EE6                                        |             38 |      37
 RUBIgGV                                    |             38 |      38
 Factor VII                                 |             36 |      33
 COV12IC                                    |             36 |      36
 COV12MC                                    |             36 |      36
 EE1                                        |             36 |      36
 Renal Epithelial Cells                     |             35 |      35
 EE2                                        |             34 |      33
 Mumps IgG Ab Value                         |             34 |      34
 Von Willebrand Factor Activity             |             32 |      26
 Amikacin                                   |             31 |      26
 Rubeola IgG Ab Value                       |             30 |      30
 Length of Urine Collection                 |             29 |      27
 Urine Volume                               |             29 |      27
 WBC Casts                                  |             29 |      29
 Homocysteine                               |             28 |      26
 Hemoglobin C                               |             28 |      28
 Hemogloblin A                              |             28 |      28
 Hemogloblin S                              |             28 |      28
 Bacteria                                   |             28 |      28
 Bilirubin, Total, Body Fluid               |             27 |      24
 EE7                                        |             26 |      26
 dRVVT - Confirmation                       |             26 |      26
 dRVVT - Normalized Ratio                   |             26 |      26
 Serum Viscosity                            |             24 |      23
 Hemoglobin A2                              |             23 |      23
 Creatinine, Body Fluid                     |             23 |      20
 Thyroid Peroxidase Antibodies              |             21 |      21
 HIV 1 Viral Load                           |             21 |      21
 Hemoglobin F                               |             20 |      20
 Broad Casts                                |             19 |      19
 HPE8                                       |             19 |      19
 Follicle Stimulating Hormone               |             19 |      19
 Factor V                                   |             18 |      18
 Toxoplasma IgM Ab Value                    |             18 |      18
 24 hr Creatinine                           |             17 |      17
 Hypersegmented Neutrophils                 |             17 |      17
 Methotrexate                               |             17 |      13
 Luteinizing Hormone                        |             16 |      16
 Waxy Casts                                 |             15 |      15
 Hematocrit, Joint Fluid                    |             15 |      15
 Factor XI                                  |             15 |      12
 Human Chorionic Gonadotropin               |             14 |      12
 EE5                                        |             14 |      14
 HBV VL CT                                  |             14 |      14
 H. pylori IgG Ab Value                     |             13 |      13
 Ethylene Glycol                            |             13 |       8
 Bilirubin, Total, Pleural                  |             13 |      13
 Triglycerides, Ascites                     |             13 |      13
 RdRP Ct                                    |             12 |      12
 Factor X                                   |             12 |      12
 Factor IX                                  |             12 |      12
 RdRP Endpt                                 |             12 |      12
 Urine Casts, Other                         |             12 |      12
 HIT-Ab Numerical Result                    |             12 |      12
 EE3                                        |             11 |      11
 Glucose, Urine                             |             11 |      11
 Cytomegalovirus Viral Load                 |             10 |      10
 Triglycer                                  |             10 |      10
 Nucleated RBC                              |              9 |       9
 24 hr Protein                              |              9 |       9
 RBC Casts                                  |              8 |       8
 Factor II                                  |              8 |       8
 Thyroglobulin                              |              8 |       8
 wbcp                                       |              7 |       7
 CD3 %                                      |              7 |       7
 CD3 Absolute Count                         |              7 |       7
 Lipase, Ascites                            |              7 |       6
 Hematocrit, CSF                            |              7 |       5
 Testosterone                               |              7 |       7
 Anti-DGP (IgA/IgG)                         |              6 |       6
 Protein C, Antigen                         |              6 |       6
 Cancer Antigen 27.29                       |              6 |       6
 UTX9                                       |              6 |       6
 Amylase/Creatinine Ratio, Urine            |              5 |       5
 Protein S, Antigen                         |              5 |       5
 Reflex Confirmatory Hepatitis C Viral Load |              5 |       5
 Urea Nitrogen, Body Fluid                  |              5 |       5
 Theophylline                               |              5 |       5
 Amylase, Urine                             |              5 |       5
 High-Sensitivity CRP                       |              5 |       5
 PAN3                                       |              5 |       5
 Eosinophil Count                           |              5 |       5
 CD16/56%                                   |              4 |       4
 Fetal Hemoglobin                           |              4 |       4
 Sodium, Body Fluid                         |              4 |       4
 Sex Hormone Binding Globulin               |              4 |       4
 Osmolality, Stool                          |              4 |       4
 HIV Viral Load Ct                          |              4 |       4
 CD5 %                                      |              4 |       4
 Potassium, Body Fluid                      |              4 |       4
 CD5 Absolute Count                         |              4 |       4
 CD16/56 Absolute Count                     |              4 |       4
 Young Cells                                |              3 |       3
 Potassium, Stool                           |              3 |       3
 Sodium, Stool                              |              3 |       3
 Hypochromia                                |              3 |       3
 Hepatitis B Viral Load                     |              3 |       3
 Hemoglobin Other                           |              3 |       3
 Cholesterol, Body Fluid                    |              3 |       3
 Chloride, Stool                            |              3 |       3
 Bicarbonate, Other Fluid                   |              3 |       3
 Microcytes                                 |              2 |       2
 Calculated Free Testosterone               |              2 |       2
 Cholesterol, Ascites                       |              2 |       2
 NonSquamous Epithelial Cell                |              2 |       2
 CD20 Absolute Count                        |              2 |       2
 HPE9                                       |              2 |       2
 Bicarbonate, Stool                         |              2 |       2
 DHEA-Sulfate                               |              2 |       2
 CD20 %                                     |              2 |       2
 K (GREEN)                                  |              2 |       2
 Anti-Thyroglobulin Antibodies              |              2 |       2
 Osmolality, Body Fluid                     |              2 |       2
 CD19 Absolute Count                        |              2 |       2
 PAN2                                       |              2 |       2
 CD19 %                                     |              2 |       2
 Lipase, Body Fluid                         |              2 |       2
 Chloride, Body Fluid                       |              2 |       2
 Macrocytes                                 |              2 |       2
 Urine Creatinine                           |              1 |       1
 Urine Volume, Total                        |              1 |       1
 CD19                                       |              1 |       1
 SCT - Confirmation                         |              1 |       1
 Blood Parasite Smear                       |              1 |       1
 Non-squamous Epithelial Cells              |              1 |       1
 Bilirubin, Total, CSF                      |              1 |       1
 RBC Morphology                             |              1 |       1
 Bicarbonate, Ascites                       |              1 |       1
 Basophilic Stippling                       |              1 |       1
 PAN                                        |              1 |       1
 Poikilocytosis                             |              1 |       1
 Factor VIII Inhibitor                      |              1 |       1
 Total Collection Time                      |              1 |       1
 Hepatitis B Surface Antibody               |              1 |       1
 Factor XII                                 |              1 |       1
 Estradiol                                  |              1 |       1
 Epstein-Barr Virus Interpretation          |              1 |       1
 Teardrop Cells                             |              1 |       1
 Target Cells                               |              1 |       1
 Howell-Jolly Bodies                        |              1 |       1
 Creatinine, Serum                          |              1 |       1
 Creatinine Clearance                       |              1 |       1
 Polychromasia                              |              1 |       1
 Spherocytes                                |              1 |       1
 Potassium, Pleural                         |              1 |       1
 Leukocyte Alkaline Phosphatase             |              1 |       1
 Sodium, Pleural                            |              1 |       1
 Sickle Cells                               |              1 |       1
 CD34                                       |              1 |       1
 Lipase, Pleural                            |              1 |       1
 CD3                                        |              1 |       1
 SCT - Normalized Ratio                     |              1 |       1
(473 rows)
*/
