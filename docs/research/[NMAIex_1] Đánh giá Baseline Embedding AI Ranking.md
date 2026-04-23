# **BÃ¡o cÃ¡o NghiÃªn cá»©u Ká»¹ thuáº­t: Thiáº¿t káº¿ vÃ  ÄÃ¡nh giÃ¡ Baseline Retrieval/Ranking cho Há»‡ thá»‘ng AI Tuyá»ƒn dá»¥ng**

## **1\. Bá»‘i cáº£nh Há»‡ thá»‘ng vÃ  PhÃ¢n tÃ­ch Cáº¥u trÃºc AI Core (FANG)**

Sá»± dá»‹ch chuyá»ƒn kiáº¿n trÃºc cá»§a há»‡ thá»‘ng tuyá»ƒn dá»¥ng tá»« mÃ´ hÃ¬nh phÃ¢n tÃ¡n sang kiáº¿n trÃºc táº­p trung, trong Ä‘Ã³ miCareer-mini trá»Ÿ thÃ nh má»™t thin client vÃ  giao phÃ³ toÃ n bá»™ trá»ng trÃ¡ch xá»­ lÃ½ dá»¯ liá»‡u ngÃ´n ngá»¯ tá»± nhiÃªn (NLP), nhÃºng vector (embedding) vÃ  tÃ¬m kiáº¿m (vector search) cho há»‡ thá»‘ng AI Core trung tÃ¢m (FANG), Ä‘Ã²i há»i má»™t chiáº¿n lÆ°á»£c Ä‘Ã¡nh giÃ¡ vÃ  thiáº¿t káº¿ láº¡i cÆ¡ cháº¿ xáº¿p háº¡ng (ranking) vÃ´ cÃ¹ng nghiÃªm ngáº·t.1 Há»‡ thá»‘ng FANG v2 hiá»‡n táº¡i Ä‘Ã£ xÃ¢y dá»±ng Ä‘Æ°á»£c má»™t ná»n táº£ng háº¡ táº§ng khÃ¡ hoÃ n thiá»‡n, bao gá»“m quy trÃ¬nh tiáº¿p nháº­n dá»¯ liá»‡u (ingestion), bá»™ phÃ¢n tÃ­ch cÃº phÃ¡p (parser) 5 táº§ng phá»©c táº¡p, chiáº¿n lÆ°á»£c phÃ¢n Ä‘oáº¡n vÄƒn báº£n nháº­n thá»©c cáº¥u trÃºc (structure-aware chunking), vÃ  há»‡ thá»‘ng lÆ°u trá»¯ vector máº¡nh máº½ trÃªn PostgreSQL.1

### **1.1. Hiá»‡n tráº¡ng Háº¡ táº§ng Dá»¯ liá»‡u vÃ  Vector Search**

Viá»‡c Ä‘Ã¡nh giÃ¡ báº¥t ká»³ Ä‘Æ°á»ng cÆ¡ sá»Ÿ (baseline) nÃ o cÅ©ng pháº£i báº¯t Ä‘áº§u tá»« viá»‡c hiá»ƒu rÃµ giá»›i háº¡n vÃ  nÄƒng lá»±c cá»§a háº¡ táº§ng lÆ°u trá»¯ vÃ  truy xuáº¥t hiá»‡n cÃ³. Há»‡ thá»‘ng FANG Ä‘ang lÆ°u trá»¯ cÃ¡c biá»ƒu diá»…n vector trong báº£ng AIDOCUMENTCHUNK cá»§a cÆ¡ sá»Ÿ dá»¯ liá»‡u PostgreSQL thÃ´ng qua tiá»‡n Ã­ch má»Ÿ rá»™ng pgvector.1

Äáº·c táº£ ká»¹ thuáº­t hiá»‡n táº¡i cho tháº¥y viá»‡c nhÃºng dá»¯ liá»‡u Ä‘Æ°á»£c thá»±c hiá»‡n bá»Ÿi mÃ´ hÃ¬nh text-embedding-3-small cá»§a OpenAI, táº¡o ra cÃ¡c vector cÃ³ sá»‘ chiá»u lÃ  1024\.1 Má»™t Ä‘iá»ƒm Ä‘Ã¡ng chÃº Ã½ trong thiáº¿t káº¿ lÃ  há»‡ thá»‘ng Ä‘ang sá»­ dá»¥ng kiá»ƒu dá»¯ liá»‡u halfvec(1024) â€“ tá»©c lÃ  sá»‘ thá»±c dáº¥u pháº©y Ä‘á»™ng bÃ¡n Ä‘á»™ chÃ­nh xÃ¡c (16-bit) â€“ lÃ m cáº¥u hÃ¬nh máº·c Ä‘á»‹nh cho cÃ¡c mÃ´i trÆ°á»ng phÃ¡t triá»ƒn vÃ  kiá»ƒm thá»­ nháº±m tá»‘i Æ°u hÃ³a dung lÆ°á»£ng RAM vÃ  kÃ­ch thÆ°á»›c chá»‰ má»¥c.1 Chá»‰ má»¥c (index) Ä‘Æ°á»£c xÃ¢y dá»±ng dá»±a trÃªn thuáº­t toÃ¡n HNSW (Hierarchical Navigable Small World) vá»›i cÃ¡c tham sá»‘ siÃªu liÃªn káº¿t ![][image1] vÃ  ![][image2], sá»­ dá»¥ng lá»›p toÃ¡n tá»­ halfvec\_cosine\_ops Ä‘á»ƒ thá»±c thi phÃ©p Ä‘o khoáº£ng cÃ¡ch Ä‘á»™ tÆ°Æ¡ng Ä‘á»“ng Cosine (Cosine Similarity).1

BÃªn cáº¡nh Ä‘Ã³, dá»¯ liá»‡u nghiá»‡p vá»¥ lÃµi (Web Core) cÆ° trÃº táº¡i micareer\_lite\_db chá»©a Ä‘á»±ng máº¡ng lÆ°á»›i dá»¯ liá»‡u quan há»‡ phong phÃº. Há»“ sÆ¡ á»©ng viÃªn (Candidate Profile) Ä‘Æ°á»£c cáº¥u trÃºc hÃ³a qua cÃ¡c báº£ng user, CANDIDATE, vÃ  CANDIDATESKILL, lÆ°u trá»¯ cÃ¡c thÃ´ng tin tá»« vÄƒn báº£n tá»± do (bio) Ä‘áº¿n dá»¯ liá»‡u Ä‘á»‹nh lÆ°á»£ng (expyears, dob) vÃ  dá»¯ liá»‡u phÃ¢n loáº¡i (prov, stat).1 TÆ°Æ¡ng tá»±, tin tuyá»ƒn dá»¥ng (Job Posting) Ä‘Æ°á»£c phÃ¢n giáº£i qua cÃ¡c báº£ng JOBPOSTING, JOBREQUIREMENT, vÃ  COMPANY, mang theo cÃ¡c siÃªu dá»¯ liá»‡u then chá»‘t nhÆ° khoáº£ng lÆ°Æ¡ng (minSalary, maxSalary), Ä‘á»‹a Ä‘iá»ƒm lÃ m viá»‡c (workLoc), vÃ  hÃ¬nh thá»©c lÃ m viá»‡c (workMode).1 Sá»± tá»“n táº¡i song song cá»§a dá»¯ liá»‡u phi cáº¥u trÃºc (Ä‘Æ°á»£c vector hÃ³a) vÃ  dá»¯ liá»‡u cÃ³ cáº¥u trÃºc (truy váº¥n báº±ng SQL) Ä‘á»‹nh hÃ¬nh trá»±c tiáº¿p con Ä‘Æ°á»ng xÃ¢y dá»±ng há»‡ thá»‘ng Ä‘á»‘i khá»›p (matching) hiá»‡u quáº£.

### **1.2. Má»¥c tiÃªu Kháº£o nghiá»‡m**

Máº·c dÃ¹ FANG v2 há»— trá»£ máº¡nh máº½ cÃ¡c luá»“ng RAG (Retrieval-Augmented Generation) cho viá»‡c truy váº¥n lá»‹ch sá»­ á»©ng viÃªn qua endpoint POST /v2/chat/query, tÃ i liá»‡u há»£p Ä‘á»“ng API (API contract) hiá»‡n hÃ nh cho tháº¥y FANG chÆ°a cung cáº¥p sáºµn logic Ä‘á»‘i khá»›p (ranking) hai chiá»u giá»¯a danh sÃ¡ch cÃ´ng viá»‡c vÃ  danh sÃ¡ch á»©ng viÃªn.1 CÃ¡c thao tÃ¡c nÃ y hiá»‡n váº«n do client tá»± xá»­ lÃ½ thÃ´ng qua truy váº¥n cÆ¡ sá»Ÿ dá»¯ liá»‡u truyá»n thá»‘ng.1 Do Ä‘Ã³, trá»ng tÃ¢m cá»§a nghiÃªn cá»©u nÃ y lÃ  thiáº¿t láº­p má»™t há»‡ thá»‘ng Ä‘Ã¡nh giÃ¡ Ä‘Æ°á»ng cÆ¡ sá»Ÿ (baseline evaluation protocol) nghiÃªm tÃºc, khoa há»c Ä‘á»ƒ xÃ¡c Ä‘á»‹nh xem liá»‡u viá»‡c káº¿t há»£p embedding hiá»‡n cÃ³ vá»›i cÃ¡c bá»™ lá»c heuristic cÃ³ Ä‘á»§ kháº£ nÄƒng giáº£i quyáº¿t bÃ i toÃ¡n ranking hai chiá»u hay khÃ´ng, trÆ°á»›c khi Ä‘á» xuáº¥t báº¥t ká»³ sá»± thay Ä‘á»•i kiáº¿n trÃºc tá»‘n kÃ©m nÃ o.

## **2\. Äáº·c táº£ BÃ i toÃ¡n Äá»‘i khá»›p Tuyá»ƒn dá»¥ng vÃ  TÃ­nh Báº¥t Ä‘á»‘i xá»©ng**

LÄ©nh vá»±c tuyá»ƒn dá»¥ng trá»±c tuyáº¿n hoáº¡t Ä‘á»™ng dÆ°á»›i má»™t sá»± máº¥t cÃ¢n báº±ng thÃ´ng tin nghiÃªm trá»ng: ngÆ°á»i tÃ¬m viá»‡c pháº£i duyá»‡t qua hÃ ng váº¡n tin tuyá»ƒn dá»¥ng thay Ä‘á»•i liÃªn tá»¥c, trong khi nhÃ  tuyá»ƒn dá»¥ng bá»‹ quÃ¡ táº£i bá»Ÿi há»“ sÆ¡ á»©ng tuyá»ƒn á»“ áº¡t nhÆ°ng cÃ³ Ä‘á»™ phÃ¹ há»£p tháº¥p.2 Viá»‡c coi Ä‘á»‘i khá»›p tuyá»ƒn dá»¥ng Ä‘Æ¡n thuáº§n lÃ  má»™t bÃ i toÃ¡n tÃ­nh Ä‘iá»ƒm tÆ°Æ¡ng Ä‘á»“ng vÄƒn báº£n (text similarity) sáº½ dáº«n Ä‘áº¿n nhá»¯ng tháº¥t báº¡i trong triá»ƒn khai thá»±c táº¿. Sá»± khÃ¡c biá»‡t cá»‘t lÃµi náº±m á»Ÿ tÃ­nh báº¥t Ä‘á»‘i xá»©ng giá»¯a hai luá»“ng tÃ¬m kiáº¿m.

### **2.1. TÃ­nh Báº¥t Ä‘á»‘i xá»©ng: Candidate-to-Job vÃ  Job-to-Candidate**

Há»‡ thá»‘ng báº¯t buá»™c pháº£i tÃ¡ch biá»‡t baseline cho luá»“ng á»©ng viÃªn tÃ¬m viá»‡c (Candidate ![][image3] Job) vÃ  luá»“ng cÃ´ng viá»‡c tÃ¬m á»©ng viÃªn (Job ![][image3] Candidate), bá»Ÿi vÃ¬ báº£n cháº¥t cá»§a quÃ¡ trÃ¬nh ra quyáº¿t Ä‘á»‹nh, bá»™ lá»c vÃ  loáº¡i hÃ¬nh suy luáº­n (reasoning types) á»Ÿ hai phÃ­a lÃ  hoÃ n toÃ n khÃ¡c nhau.3

| Äáº·c Ä‘iá»ƒm | Job â†’ Candidate (NhÃ  tuyá»ƒn dá»¥ng tÃ¬m á»¨ng viÃªn) | Candidate â†’ Job (á»¨ng viÃªn tÃ¬m CÃ´ng viá»‡c) |
| :---- | :---- | :---- |
| **Báº£n cháº¥t Suy luáº­n** | **Parallel Reasoning (Suy luáº­n Song song):** Há»‡ thá»‘ng pháº£i kiá»ƒm tra Ä‘á»“ng thá»i nhiá»u rÃ ng buá»™c cá»©ng kháº¯t khe.5 | **Serial/Multi-hop Reasoning (Suy luáº­n Chuá»—i):** Há»‡ thá»‘ng cáº§n suy luáº­n vá» ká»¹ nÄƒng chuyá»ƒn Ä‘á»•i (transferable skills) vÃ  tiá»m nÄƒng phÃ¡t triá»ƒn.5 |
| **Äá»™ nháº¡y cáº£m RÃ ng buá»™c** | Ráº¥t cao. Má»™t á»©ng viÃªn cÃ³ bá»™ ká»¹ nÄƒng hoÃ n háº£o nhÆ°ng thiáº¿u 2 nÄƒm kinh nghiá»‡m báº¯t buá»™c sáº½ bá»‹ loáº¡i ngay láº­p tá»©c (Hard Filter). | Tháº¥p hÆ¡n. á»¨ng viÃªn cÃ³ xu hÆ°á»›ng ná»™p há»“ sÆ¡ vÃ o cÃ¡c vá»‹ trÃ­ yÃªu cáº§u cao hÆ¡n hoáº·c á»Ÿ Ä‘á»‹a Ä‘iá»ƒm lÃ¢n cáº­n náº¿u má»©c lÆ°Æ¡ng Ä‘á»§ háº¥p dáº«n (Soft Preference). |
| **Má»¥c tiÃªu Tá»‘i Æ°u** | **Precision (Äá»™ chuáº©n xÃ¡c):** Quá»¹ thá»i gian cá»§a nhÃ  tuyá»ƒn dá»¥ng ráº¥t giá»›i háº¡n (chá»‰ vÃ i giÃ¢y má»—i CV) 7, do Ä‘Ã³ káº¿t quáº£ hiá»ƒn thá»‹ trÃªn cÃ¹ng (Top-K) pháº£i hoÃ n toÃ n khá»›p vá»›i JD. | **Recall & Diversity (Äá»™ phá»§ vÃ  Äa dáº¡ng):** Äáº£m báº£o á»©ng viÃªn khÃ´ng bá»‹ bá» lá»¡ cÃ¡c cÆ¡ há»™i nghá» nghiá»‡p mÃ  há» cÃ³ kháº£ nÄƒng Ä‘Ã¡p á»©ng thÃ´ng qua Ä‘Ã o táº¡o ngáº¯n háº¡n. |
| **Yáº¿u tá»‘ Veto (Quyá»n phá»§ quyáº¿t)** | Tráº¡ng thÃ¡i tÃ i khoáº£n (stat \= INACTIVE), thiáº¿u ká»¹ nÄƒng lÃµi (skillId), khoáº£ng cÃ¡ch Ä‘á»‹a lÃ½ khÃ´ng phÃ¹ há»£p. | Tin tuyá»ƒn dá»¥ng Ä‘Ã£ háº¿t háº¡n (expAt \< NOW), má»©c lÆ°Æ¡ng (maxSalary) tháº¥p hÆ¡n ká»³ vá»ng tá»‘i thiá»ƒu. |

Viá»‡c sá»­ dá»¥ng chung má»™t cÃ´ng thá»©c Cosine(Vector\_CV, Vector\_JD) cho cáº£ hai luá»“ng sáº½ táº¡o ra hiá»‡n tÆ°á»£ng sai sá»‘ há»‡ thá»‘ng. VÃ­ dá»¥, má»™t nhÃ  tuyá»ƒn dá»¥ng tÃ¬m "Senior Java Developer vá»›i 5 nÄƒm kinh nghiá»‡m", vector embedding cÃ³ thá»ƒ tráº£ vá» má»™t "Junior Java Developer vá»›i 1 nÄƒm kinh nghiá»‡m" á»Ÿ thá»© háº¡ng cao vÃ¬ ná»™i dung cÃ´ng nghá»‡ (Java, Spring Boot, Microservices) trÃ¹ng khá»›p máº¡nh máº½.8 Trong khi Ä‘Ã³, vá»›i luá»“ng Candidate ![][image3] Job, viá»‡c gá»£i Ã½ vá»‹ trÃ­ Senior cho má»™t Junior láº¡i cÃ³ thá»ƒ lÃ  má»™t chiáº¿n lÆ°á»£c khuyáº¿n khÃ­ch á»©ng viÃªn vÆ°Æ¡n lÃªn, tÃ¹y thuá»™c vÃ o ngÆ°á»¡ng Ä‘iá»ƒm Ä‘Ã¡nh giÃ¡.

### **2.2. NhÃ£n Dá»¯ liá»‡u vÃ  Nguy cÆ¡ RÃ² rá»‰ (Data Leakage)**

Má»™t thÃ¡ch thá»©c lá»›n trong viá»‡c Ä‘Ã¡nh giÃ¡ cÃ¡c há»‡ thá»‘ng Applicant Tracking System (ATS) lÃ  sá»± thiáº¿u há»¥t cÃ¡c nhÃ£n Ä‘Ã¡nh giÃ¡ Ä‘á»™ phÃ¹ há»£p thá»±c táº¿ (ground truth labels).9 Há»‡ thá»‘ng truyá»n thá»‘ng thÆ°á»ng sá»­ dá»¥ng dá»¯ liá»‡u tÆ°Æ¡ng tÃ¡c nhÆ° lÆ°á»£t nháº¥p (click), lÆ°á»£t xem (view), hoáº·c viá»‡c á»©ng viÃªn chá»§ Ä‘á»™ng ná»™p há»“ sÆ¡ Ä‘á»ƒ lÃ m nhÃ£n "TÃ­ch cá»±c" (Positive).

Tuy nhiÃªn, viá»‡c sá»­ dá»¥ng cÃ¡c tÆ°Æ¡ng tÃ¡c bá» máº·t nÃ y dáº«n Ä‘áº¿n **rÃ² rá»‰ dá»¯ liá»‡u (Data Leakage)** vÃ  **thiÃªn vá»‹ (Bias)**. Má»™t á»©ng viÃªn ná»™p há»“ sÆ¡ khÃ´ng cÃ³ nghÄ©a lÃ  há» phÃ¹ há»£p vá»›i cÃ´ng viá»‡c Ä‘Ã³.10 NgÆ°á»£c láº¡i, náº¿u chá»‰ dá»±a vÃ o quyáº¿t Ä‘á»‹nh má»i phá»ng váº¥n cá»§a nhÃ  tuyá»ƒn dá»¥ng Ä‘á»ƒ lÃ m nhÃ£n, há»‡ thá»‘ng AI sáº½ vÃ´ tÃ¬nh há»c vÃ  khuáº¿ch Ä‘áº¡i nhá»¯ng thiÃªn kiáº¿n áº©n (unconscious bias) cá»§a con ngÆ°á»i vá» giá»›i tÃ­nh, Ä‘á»™ tuá»•i, hoáº·c trÆ°á»ng Ä‘áº¡i há»c.4

Giao thá»©c Ä‘Ã¡nh giÃ¡ cáº§n pháº£i Ä‘o lÆ°á»ng "Äá»™ phÃ¹ há»£p NÄƒng lá»±c" (Competency Alignment) thá»±c cháº¥t thay vÃ¬ Ä‘o lÆ°á»ng kháº£ nÄƒng trÃºng tuyá»ƒn bá»‹ nhiá»…u bá»Ÿi yáº¿u tá»‘ ngoáº¡i cáº£nh.5 CÃ¡c nhÃ£n sá»­ dá»¥ng trong quÃ¡ trÃ¬nh benchmark pháº£i Ä‘Æ°á»£c Ä‘á»‹nh nghÄ©a rÃµ rÃ ng: NhÃ£n dÆ°Æ¡ng (Positive) chá»‰ Ä‘Æ°á»£c cáº¥p khi cÃ³ Ä‘á»§ báº±ng chá»©ng trong CV há»— trá»£ cÃ¡c yÃªu cáº§u trong JD.5

## **3\. Thiáº¿t káº¿ Baseline Retrieval vÃ  Ranking**

Äá»ƒ cÃ³ má»™t sá»± so sÃ¡nh cÃ´ng báº±ng vÃ  khoa há»c, baseline pháº£i Ä‘Æ°á»£c xÃ¢y dá»±ng tá»« má»©c Ä‘á»™ cÆ¡ báº£n nháº¥t Ä‘áº¿n cÃ¡c phÆ°Æ¡ng phÃ¡p tiÃªn tiáº¿n, Ä‘áº£m báº£o phÃ¹ há»£p vá»›i khá»‘i lÆ°á»£ng dá»¯ liá»‡u thá»±c táº¿ cá»§a ATS. QuÃ¡ trÃ¬nh nÃ y khÃ´ng thá»ƒ chá»‰ dá»±a vÃ o má»™t lá»‡nh tÃ¬m kiáº¿m ORDER BY embedding \<=\> query\_embedding 1, bá»Ÿi giá»›i háº¡n lÃ½ thuyáº¿t cá»§a vector máº­t Ä‘á»™ (Dense Vector) Ä‘Ã£ Ä‘Æ°á»£c chá»©ng minh: má»™t mÃ´ hÃ¬nh vector Ä‘Æ¡n láº» khÃ´ng thá»ƒ phÃ¢n hoáº¡ch khÃ´ng gian hÃ¬nh há»c Ä‘á»ƒ thá»a mÃ£n tÃ­nh phá»©c táº¡p tá»• há»£p cá»§a cÃ¡c truy váº¥n.13

### **3.1. CÃ¡c PhÆ°Æ¡ng Ã¡n Baseline Äá» xuáº¥t vÃ  Lá»±a chá»n**

DÆ°á»›i Ä‘Ã¢y lÃ  cÃ¡c phÆ°Æ¡ng Ã¡n kiáº¿n trÃºc Baseline Ä‘Æ°á»£c phÃ¢n tÃ­ch, xáº¿p háº¡ng theo má»©c Ä‘á»™ phÃ¹ há»£p vá»›i há»‡ thá»‘ng FANG hiá»‡n táº¡i:

1. **Háº¡ng 3 (KÃ©m phÃ¹ há»£p nháº¥t): Cosine Similarity Thuáº§n TÃºy**  
   * *Kiáº¿n trÃºc:* Chá»‰ sá»­ dá»¥ng toÃ¡n tá»­ halfvec\_cosine\_ops trÃªn báº£ng AIDOCUMENTCHUNK.1  
   * *NhÆ°á»£c Ä‘iá»ƒm:* Bá» qua hoÃ n toÃ n cÃ¡c siÃªu dá»¯ liá»‡u cáº¥u trÃºc nhÆ° nÄƒm kinh nghiá»‡m, má»©c lÆ°Æ¡ng, vÃ  ká»¹ nÄƒng báº¯t buá»™c. ThÆ°á»ng xuyÃªn tráº£ vá» cÃ¡c káº¿t quáº£ cÃ³ Ä‘á»™ tÆ°Æ¡ng Ä‘á»“ng ngá»¯ nghÄ©a cao nhÆ°ng sai lá»‡ch nghiÃªm trá»ng vá» cáº¥p Ä‘á»™ chuyÃªn mÃ´n (Senior vs Intern).  
2. **Háº¡ng 2 (Äáº¡t yÃªu cáº§u tá»‘i thiá»ƒu): Vector Retrieval \+ Heuristic Filter (Hard Filtering)**  
   * *Kiáº¿n trÃºc:* Sá»­ dá»¥ng SQL Ä‘á»ƒ lá»c cÃ¡c rÃ ng buá»™c cá»©ng trÆ°á»›c (vÃ­ dá»¥: WHERE expyears \>= 3 AND workLoc \= 'Hanoi'), sau Ä‘Ã³ tÃ­nh Cosine Similarity trÃªn cÃ¡c há»“ sÆ¡ cÃ²n láº¡i.  
   * *Æ¯u Ä‘iá»ƒm:* Giáº£i quyáº¿t ngay láº­p tá»©c cÃ¡c lá»—i sai lá»‡ch cáº¥p Ä‘á»™ vÃ  Ä‘á»‹a lÃ½. Dá»… dÃ ng triá»ƒn khai báº±ng SQL káº¿t há»£p pgvector.  
   * *NhÆ°á»£c Ä‘iá»ƒm:* QuÃ¡ cá»©ng nháº¯c. Viá»‡c thiáº¿u má»™t tá»« khÃ³a chÃ­nh xÃ¡c cÃ³ thá»ƒ loáº¡i bá» hoÃ n toÃ n má»™t á»©ng viÃªn xuáº¥t sáº¯c sá»Ÿ há»¯u tá»« khÃ³a Ä‘á»“ng nghÄ©a nhÆ°ng chÆ°a Ä‘Æ°á»£c chuáº©n hÃ³a.14  
3. **Háº¡ng 1 (Tá»‘i Æ°u nháº¥t cho FANG): Hybrid Search \+ Linear Scoring (Xáº¿p háº¡ng Tuyáº¿n tÃ­nh Lai)**  
   * *Kiáº¿n trÃºc:* Káº¿t há»£p Ä‘iá»ƒm sá»‘ truy xuáº¥t ngá»¯ nghÄ©a (Dense Vector Search) vá»›i Ä‘iá»ƒm sá»‘ truy xuáº¥t tá»« khÃ³a/siÃªu dá»¯ liá»‡u (Metadata/Sparse Matching), vÃ  há»£p nháº¥t chÃºng báº±ng má»™t hÃ m tuyáº¿n tÃ­nh cÃ³ trá»ng sá»‘.15  
   * *LÃ½ do lá»±a chá»n:* CÆ¡ sá»Ÿ dá»¯ liá»‡u micareer\_lite\_db Ä‘Ã£ cÃ³ sáºµn cÃ¡c báº£ng quan há»‡ CANDIDATESKILL vÃ  JOBREQUIREMENT.1 Viá»‡c táº­n dá»¥ng dá»¯ liá»‡u cáº¥u trÃºc nÃ y káº¿t há»£p vá»›i kháº£ nÄƒng hiá»ƒu ngá»¯ cáº£nh cá»§a vector embedding táº¡o ra má»™t há»‡ thá»‘ng Ä‘á»‘i khá»›p Ä‘a chiá»u. Linear Scoring cho phÃ©p hiá»‡u chá»‰nh trá»ng sá»‘ (calibration) tÃ¹y theo tÃ­nh cháº¥t cá»§a tá»«ng vá»‹ trÃ­ tuyá»ƒn dá»¥ng.

### **3.2. RRF so vá»›i Káº¿t há»£p Tuyáº¿n tÃ­nh (Linear Combination)**

Khi há»£p nháº¥t hai táº­p káº¿t quáº£ tá»« Vector Search vÃ  Metadata Search, ngÃ nh cÃ´ng nghiá»‡p thÆ°á»ng tranh luáº­n giá»¯a Reciprocal Rank Fusion (RRF) vÃ  Linear Combination.17

* **Reciprocal Rank Fusion (RRF):** PhÆ°Æ¡ng phÃ¡p nÃ y loáº¡i bá» Ä‘iá»ƒm sá»‘ thÃ´ vÃ  chá»‰ dá»±a vÃ o thá»© háº¡ng (rank). CÃ´ng thá»©c ![][image4] táº¡o ra sá»± á»•n Ä‘á»‹nh khi káº¿t há»£p cÃ¡c há»‡ thá»‘ng cÃ³ thang Ä‘iá»ƒm khÃ¡c nhau.19 RRF ráº¥t dá»… triá»ƒn khai "out-of-the-box".  
* **Linear Combination (Káº¿t há»£p Tuyáº¿n tÃ­nh):** YÃªu cáº§u chuáº©n hÃ³a Ä‘iá»ƒm sá»‘ (vÃ­ dá»¥: Min-Max scaling) trÆ°á»›c khi nhÃ¢n vá»›i trá»ng sá»‘ ![][image5] vÃ  ![][image6]. ![][image7]. PhÆ°Æ¡ng phÃ¡p nÃ y tÃ´n trá»ng Ä‘á»™ lá»›n cá»§a Ä‘iá»ƒm sá»‘ (magnitude of scores).

**Quyáº¿t Ä‘á»‹nh Ká»¹ thuáº­t:** Äá»‘i vá»›i bÃ i toÃ¡n tuyá»ƒn dá»¥ng, **Linear Combination lÃ  phÆ°Æ¡ng Ã¡n vÆ°á»£t trá»™i hÆ¡n**.16 RRF cÃ³ má»™t Ä‘iá»ƒm yáº¿u chÃ­ máº¡ng trong tuyá»ƒn dá»¥ng: nÃ³ lÃ m máº¥t Ä‘i sá»± trá»«ng pháº¡t vá» máº·t Ä‘iá»ƒm sá»‘ Ä‘á»‘i vá»›i cÃ¡c há»“ sÆ¡ thiáº¿u há»¥t ká»¹ nÄƒng tráº§m trá»ng. Náº¿u má»™t JD yÃªu cáº§u 5 ká»¹ nÄƒng, vÃ  á»©ng viÃªn chá»‰ cÃ³ 1 ká»¹ nÄƒng, Ä‘iá»ƒm sá»‘ heuristic sáº½ ráº¥t tháº¥p, nhÆ°ng RRF cÃ³ thá»ƒ váº«n Ä‘áº©y á»©ng viÃªn nÃ y lÃªn cao náº¿u vector search vÃ´ tÃ¬nh xáº¿p háº¡ng cao do vÄƒn phong tÆ°Æ¡ng Ä‘á»“ng. Linear Scoring cho phÃ©p gÃ¡n má»™t trá»ng sá»‘ phá»§ quyáº¿t lá»›n vÃ o bá»™ lá»c ká»¹ nÄƒng cá»©ng.

### **3.3. Xá»­ lÃ½ vÃ  Chuáº©n hÃ³a VÄƒn báº£n TrÆ°á»›c NhÃºng (Pre-embedding Text Normalization)**

Cháº¥t lÆ°á»£ng cá»§a vector embedding phá»¥ thuá»™c trá»±c tiáº¿p vÃ o vÄƒn báº£n Ä‘áº§u vÃ o. Dá»¯ liá»‡u CV vÃ  JD thÆ°á»ng chá»©a ráº¥t nhiá»u nhiá»…u, mÃ£ hÃ³a sai, vÃ  Ä‘á»‹nh dáº¡ng phi cáº¥u trÃºc.23 Do FANG v2 sá»­ dá»¥ng bá»™ phÃ¢n tÃ­ch cÃº phÃ¡p (Parser) 5 táº§ng máº¡nh máº½ vá»›i cÃ¡c quy táº¯c Quality Gate xÃ¡c Ä‘á»‹nh 1, há»‡ thá»‘ng cÃ³ lá»£i tháº¿ tuyá»‡t Ä‘á»‘i trong viá»‡c cáº¥u trÃºc hÃ³a trÆ°á»›c khi nhÃºng.

Baseline cáº§n xá»­ lÃ½ cÃ¡c trÆ°á»ng dá»¯ liá»‡u theo quy trÃ¬nh sau:

1. **LÃ m sáº¡ch TiÃªu chuáº©n:** Loáº¡i bá» cÃ¡c tháº» HTML, kÃ½ tá»± phi ASCII, stopwords khÃ´ng mang Ã½ nghÄ©a, vÃ  chuyá»ƒn Ä‘á»•i chá»¯ thÆ°á»ng (lowercase) toÃ n bá»™ há»‡ thá»‘ng Ä‘á»ƒ Ä‘áº£m báº£o tÃ­nh nháº¥t quÃ¡n.23  
2. **Chuáº©n hÃ³a Chá»©c danh (Job Title) vÃ  LÄ©nh vá»±c (Domain):** Chá»©c danh cÃ´ng viá»‡c táº¡i Viá»‡t Nam ráº¥t Ä‘a dáº¡ng vÃ  cÃ³ sá»± pha trá»™n giá»¯a tiáº¿ng Anh vÃ  tiáº¿ng Viá»‡t (VD: "Láº­p trÃ¬nh viÃªn Frontend", "Frontend Developer", "NhÃ¢n viÃªn phÃ¡t triá»ƒn giao diá»‡n Web"). Cáº§n xÃ¢y dá»±ng má»™t tá»« Ä‘iá»ƒn Ä‘á»“ng nghÄ©a (Taxonomy/Ontology) Ä‘á»ƒ Ã¡nh xáº¡ cÃ¡c chá»©c danh nÃ y vá» má»™t ID chung hoáº·c chuá»—i chuáº©n trÆ°á»›c khi Ä‘Æ°a vÃ o embedding.26  
3. **Xá»­ lÃ½ Ká»¹ nÄƒng (Skill):** TrÃ­ch xuáº¥t ká»¹ nÄƒng thÃ nh má»™t danh sÃ¡ch Ä‘á»™c láº­p vÃ  tÃ­nh toÃ¡n Ä‘á»™ tÆ°Æ¡ng Ä‘á»“ng Jaccard (Jaccard Similarity) song song vá»›i viá»‡c lÆ°u trá»¯ ná»™i dung mÃ´ táº£ ká»¹ nÄƒng trong vector.31 Äiá»u nÃ y trÃ¡nh viá»‡c vector bá»‹ pha loÃ£ng bá»Ÿi cÃ¡c tá»« khÃ³a khÃ´ng trá»ng tÃ¢m.  
4. **Xá»­ lÃ½ Kinh nghiá»‡m (Experience) vÃ  ThÃ¢m niÃªn (Seniority):** ThÃ´ng tin Ä‘á»‹nh lÆ°á»£ng nhÆ° sá»‘ nÄƒm kinh nghiá»‡m (expyears) 1 khÃ´ng nÃªn Ä‘Æ°a vÃ o khá»‘i vÄƒn báº£n nhÃºng. Kháº£ nÄƒng hiá»ƒu cÃ¡c con sá»‘ cá»§a cÃ¡c mÃ´ hÃ¬nh embedding ráº¥t kÃ©m. Sá»‘ nÄƒm kinh nghiá»‡m cáº§n Ä‘Æ°á»£c chuyá»ƒn thÃ nh má»™t Ä‘áº·c trÆ°ng tÃ­nh toÃ¡n chÃªnh lá»‡ch (Delta Feature): ![][image8].  
5. **Xá»­ lÃ½ Äá»‹a lÃ½ (Location):** TÆ°Æ¡ng tá»± nhÆ° ká»¹ nÄƒng, Ä‘á»‹a Ä‘iá»ƒm (prov, ward) cáº§n Ä‘Æ°á»£c chuáº©n hÃ³a qua danh má»¥c hÃ nh chÃ­nh 1 Ä‘á»ƒ lÃ m bá»™ lá»c hoáº·c sá»­ dá»¥ng hÃ m suy hao khoáº£ng cÃ¡ch (distance decay) thay vÃ¬ phÃ¢n tÃ­ch ngá»¯ nghÄ©a.  
6. **Chiáº¿n lÆ°á»£c PhÃ¢n Ä‘oáº¡n (Chunking):** Viá»‡c báº£o toÃ n ngá»¯ cáº£nh phÃ¢n Ä‘oáº¡n (Section-Pinning) Ä‘ang cÃ³ sáºµn trong FANG lÃ  má»™t phÆ°Æ¡ng phÃ¡p cá»±c ká»³ hiá»‡u quáº£.1 Cáº§n Ä‘áº£m báº£o ráº±ng cÃ¡c Ä‘oáº¡n vÄƒn mÃ´ táº£ kinh nghiá»‡m (Experience) khÃ´ng bá»‹ trá»™n láº«n vá»›i má»¥c tiÃªu nghá» nghiá»‡p (Objective) trong quÃ¡ trÃ¬nh tÃ­nh toÃ¡n khoáº£ng cÃ¡ch vector.

## **4\. ÄÃ¡nh giÃ¡ MÃ´ hÃ¬nh text-embedding-3-small**

Vá»›i viá»‡c kho dá»¯ liá»‡u PostgreSQL Ä‘Ã£ Ä‘Æ°á»£c Ä‘á»‹nh dáº¡ng cho cá»™t embedding halfvec(1024) cháº¡y thuáº­t toÃ¡n HNSW cosine 1, viá»‡c ra quyáº¿t Ä‘á»‹nh giá»¯ hay thay Ä‘á»•i mÃ´ hÃ¬nh text-embedding-3-small cáº§n cÃ³ luáº­n cá»© ká»¹ thuáº­t sáº¯c bÃ©n.

### **4.1. NÄƒng lá»±c Thá»±c táº¿ vÃ  Äiá»u kiá»‡n Giá»¯ nguyÃªn**

Theo cÃ¡c bÃ i kiá»ƒm tra benchmark Ä‘á»™c láº­p, text-embedding-3-small lÃ  má»™t bÆ°á»›c nháº£y vá»t so vá»›i tháº¿ há»‡ trÆ°á»›c (ada-002). NÃ³ Ä‘áº¡t Ä‘iá»ƒm trung bÃ¬nh 62.3% trÃªn bá»™ MTEB (Ä‘á»‘i vá»›i tiáº¿ng Anh) vÃ  44.0% trÃªn bá»™ MIRACL (truy xuáº¥t Ä‘a ngÃ´n ngá»¯), trong khi chi phÃ­ cá»±c ká»³ ráº» á»Ÿ má»©c 0.02 USD/1 triá»‡u token.33

**Äiá»u kiá»‡n Ä‘á»ƒ giá»¯ nguyÃªn:**

MÃ´ hÃ¬nh nÃ y hoÃ n toÃ n Ä‘á»§ tá»‘t Ä‘á»ƒ Ä‘Ã³ng vai trÃ² lÃ m **Retriever (MÃ¡y truy xuáº¥t) á»Ÿ Giai Ä‘oáº¡n 1** cá»§a má»™t há»‡ thá»‘ng tuyá»ƒn dá»¥ng náº¿u thá»a mÃ£n cÃ¡c Ä‘iá»u kiá»‡n:

* Má»¥c tiÃªu hiá»‡n táº¡i lÃ  táº¡o ra má»™t danh sÃ¡ch á»©ng viÃªn thu gá»n (Shortlisting) Æ°u tiÃªn Ä‘á»™ phá»§ (Recall) cao.  
* Há»‡ thá»‘ng khÃ´ng yÃªu cáº§u mÃ´ hÃ¬nh nhÃºng pháº£i giáº£i quyáº¿t Ä‘Æ°á»£c tÃ­nh tá»• há»£p phá»©c táº¡p (nhÆ° kháº£ nÄƒng tá»± Ä‘á»™ng hiá»ƒu ráº±ng 5 nÄƒm kinh nghiá»‡m pháº£i Ä‘i kÃ¨m vá»›i ká»¹ nÄƒng quáº£n lÃ½).13  
* CÆ¡ sá»Ÿ háº¡ táº§ng hiá»‡n táº¡i (viá»‡c sá»­ dá»¥ng halfvec(1024)) 1 Ä‘ang Ä‘Ã¡p á»©ng Ä‘Æ°á»£c thá»i gian trá»… (latency) \< 100ms cho cÃ¡c truy váº¥n RAG.38

Sá»± káº¿t há»£p giá»¯a HNSW vÃ  halfvec cung cáº¥p tá»· lá»‡ Ä‘Ã¡nh Ä‘á»•i (trade-off) hoÃ n háº£o giá»¯a Ä‘á»™ chÃ­nh xÃ¡c vÃ  hiá»‡u nÄƒng pháº§n cá»©ng trong bÃ i toÃ¡n Semantic Retrieval (Truy xuáº¥t Ngá»¯ nghÄ©a). CÃ¡c thá»­ nghiá»‡m thá»±c táº¿ chá»©ng minh ráº±ng viá»‡c háº¡ Ä‘á»™ phÃ¢n giáº£i xuá»‘ng 16-bit gáº§n nhÆ° khÃ´ng tÃ¡c Ä‘á»™ng tiÃªu cá»±c Ä‘áº¿n chá»‰ sá»‘ NDCG hay Recall trong cÃ¡c bÃ i toÃ¡n xáº¿p háº¡ng vÄƒn báº£n.

### **4.2. Dáº¥u hiá»‡u Nháº­n biáº¿t "Bottleneck" Thá»±c sá»± cá»§a Embedding**

Máº·c dÃ¹ máº¡nh máº½, cÃ¡c mÃ´ hÃ¬nh nhÃºng má»¥c Ä‘Ã­ch chung (General-purpose embeddings) Ä‘Æ°á»£c huáº¥n luyá»‡n trÃªn dá»¯ liá»‡u web thÆ°á»ng bá»™c lá»™ nhá»¯ng khiáº¿m khuyáº¿t cháº¿t ngÆ°á»i khi Ã¡p dá»¥ng vÃ o ngÃ´n ngá»¯ chuyÃªn ngÃ nh (Domain-specific jargon) cá»§a HR. Nhá»¯ng dáº¥u hiá»‡u chá»©ng minh embedding hiá»‡n táº¡i Ä‘Ã£ trá»Ÿ thÃ nh Ä‘iá»ƒm ngháº½n (bottleneck) bao gá»“m:

1. **áº¢o giÃ¡c Ngá»¯ nghÄ©a Äáº·c thÃ¹ (Semantic Hallucination & Domain Mismatch):** NhÆ° "BÃ i toÃ¡n Java Developer" Ä‘Ã£ minh há»a.8 MÃ´ hÃ¬nh sáº½ Ä‘Ã¡nh giÃ¡ Ä‘á»™ tÆ°Æ¡ng Ä‘á»“ng Cosine ráº¥t cao (vÃ­ dá»¥: \> 0.85) giá»¯a má»™t báº£n JD tÃ¬m kiáº¿m "Java Developer" (ngÃ´n ngá»¯ biÃªn dá»‹ch, backend) vÃ  má»™t CV cá»§a "JavaScript Developer" (ngÃ´n ngá»¯ thÃ´ng dá»‹ch, frontend) chá»‰ vÃ¬ hai tá»« khÃ³a nÃ y chia sáº» gá»‘c tá»« vÃ  thÆ°á»ng xuáº¥t hiá»‡n cÃ¹ng nhau trong khÃ´ng gian vector cá»§a cÃ¡c bÃ i bÃ¡o cÃ´ng nghá»‡.  
2. **Sá»± Sá»¥p Ä‘á»• KhÃ´ng gian NhÃºng (Embedding Collapse):** Xáº£y ra khi cÃ¡c vector cÃ³ xu hÆ°á»›ng quy tá»¥ vá» má»™t khÃ´ng gian chiá»u tháº¥p do áº£nh hÆ°á»Ÿng cá»§a cÃ¡c vÄƒn báº£n ráº­p khuÃ´n.40 HÃ ng ngÃ n CV sá»­ dá»¥ng chung cÃ¡c cá»¥m tá»« sÃ¡o rá»—ng (buzzwords) nhÆ° "nÄƒng Ä‘á»™ng", "chá»‹u Ä‘Æ°á»£c Ã¡p lá»±c", "ká»¹ nÄƒng lÃ m viá»‡c nhÃ³m" sáº½ khiáº¿n vector cá»§a chÃºng gáº§n nhÆ° giá»‘ng há»‡t nhau, lÃ m lu má» cÃ¡c ká»¹ nÄƒng cÃ´ng nghá»‡ cá»‘t lÃµi, khiáº¿n mÃ´ hÃ¬nh máº¥t Ä‘i tÃ­nh phÃ¢n biá»‡t (discriminative power).41  
3. **Tháº¥t báº¡i vá»›i Truy váº¥n Tá»• há»£p (Combinatorial Query Failures):** Khi nhÃ  tuyá»ƒn dá»¥ng tÃ¬m kiáº¿m má»™t yÃªu cáº§u Ä‘a Ä‘iá»u kiá»‡n phá»©c táº¡p, vector 1024 chiá»u khÃ´ng thá»ƒ biá»ƒu diá»…n má»™t cÃ¡ch hÃ¬nh há»c táº¥t cáº£ cÃ¡c rÃ ng buá»™c Ä‘Ã³ cÃ¹ng má»™t lÃºc. Má»i sá»± ná»— lá»±c Ã©p mÃ´ hÃ¬nh vector hiá»ƒu cÃ¡c quy táº¯c cá»©ng sáº½ dáº«n Ä‘áº¿n káº¿t quáº£ tráº£ vá» lÃ  sá»± "trung bÃ¬nh hÃ³a" ná»™i dung (average context) thay vÃ¬ chÃ­nh xÃ¡c thÃ´ng tin.13

*Quyáº¿t Ä‘á»‹nh:* **NÃªn Ä‘Ã¡nh giÃ¡ embedding theo Semantic Retrieval**, chá»© khÃ´ng pháº£i theo Matching Classification hay Ranking cuá»‘i cÃ¹ng.39 Vai trÃ² cá»§a Embedding lÃ  mang láº¡i Recall cao. Viá»‡c tinh chá»‰nh (fine-tuning) cÃ¡c yáº¿u tá»‘ xáº¿p háº¡ng nÃªn dÃ nh cho hÃ m Linear Scoring á»Ÿ Giai Ä‘oáº¡n 2\.

## **5\. Giao thá»©c ÄÃ¡nh giÃ¡, So sÃ¡nh vÃ  Äo lÆ°á»ng (Evaluation Protocol)**

Trong bá»‘i cáº£nh há»‡ thá»‘ng FANG v2, nguyÃªn táº¯c cao nháº¥t lÃ  Æ°u tiÃªn cÃ¡c Ä‘á» xuáº¥t cÃ³ thá»ƒ kiá»ƒm chá»©ng báº±ng **Offline Evaluation (ÄÃ¡nh giÃ¡ ngoáº¡i tuyáº¿n)** trÆ°á»›c khi Ä‘Æ°a ra A/B testing trÃªn mÃ´i trÆ°á»ng tháº­t. Giao thá»©c Ä‘Ã¡nh giÃ¡ Ä‘á» xuáº¥t lÃ  mÃ´ hÃ¬nh PJB (Person-Job Benchmark) nháº±m cháº©n Ä‘oÃ¡n nÄƒng lá»±c há»‡ thá»‘ng.5

### **5.1. Äá»‹nh má»©c vÃ  CÃ¡c Metric ChÃ­nh**

Viá»‡c Ä‘o lÆ°á»ng há»‡ thá»‘ng Candidate Ranking khÃ´ng thá»ƒ chá»‰ dá»±a vÃ o má»™t chá»‰ sá»‘ Ä‘Æ¡n láº». Äá» xuáº¥t sá»­ dá»¥ng há»‡ thá»‘ng Metric phÃ¢n táº§ng 38:

* **Äo lÆ°á»ng nÄƒng lá»±c cá»§a Baseline Retrieval (Giai Ä‘oáº¡n 1):** Sá»­ dá»¥ng **Recall@K** (vÃ­ dá»¥: Recall@50 hoáº·c Recall@100).  
  * *Ã nghÄ©a:* Tá»· lá»‡ pháº§n trÄƒm cÃ¡c á»©ng viÃªn/cÃ´ng viá»‡c phÃ¹ há»£p (Relevant items) xuáº¥t hiá»‡n trong top K káº¿t quáº£ tráº£ vá». Náº¿u Recall tháº¥p, Ä‘iá»u Ä‘Ã³ cÃ³ nghÄ©a lÃ  mÃ´ hÃ¬nh text-embedding-3-small Ä‘Ã£ tháº¥t báº¡i trong viá»‡c náº¯m báº¯t khÃ´ng gian ngá»¯ nghÄ©a cÆ¡ báº£n, vÃ  má»i ná»— lá»±c Reranking á»Ÿ phÃ­a sau sáº½ vÃ´ nghÄ©a vÃ¬ cÃ¡c há»“ sÆ¡ tá»‘t Ä‘Ã£ bá»‹ bá» lá»t.44  
* **Äo lÆ°á»ng nÄƒng lá»±c cá»§a Xáº¿p háº¡ng Tá»•ng thá»ƒ (Giai Ä‘oáº¡n 2):** Sá»­ dá»¥ng **NDCG@10** (Normalized Discounted Cumulative Gain táº¡i Top 10).  
  * *Ã nghÄ©a:* KhÃ¡c vá»›i Precision hay Recall, NDCG cÃ³ tÃ­nh nháº­n thá»©c vá» thá»© háº¡ng (rank-aware) vÃ  há»— trá»£ nhÃ£n phÃ¢n cáº¥p (graded relevance) thay vÃ¬ chá»‰ nhá»‹ phÃ¢n (cÃ³/khÃ´ng).43 Má»™t há»“ sÆ¡ á»©ng viÃªn xuáº¥t sáº¯c Ä‘Æ°á»£c xáº¿p á»Ÿ vá»‹ trÃ­ sá»‘ 1 sáº½ nháº­n Ä‘Æ°á»£c Ä‘iá»ƒm thÆ°á»Ÿng (Gain) cao hÆ¡n nhiá»u so vá»›i viá»‡c xuáº¥t hiá»‡n á»Ÿ vá»‹ trÃ­ sá»‘ 10\. ÄÃ¢y lÃ  metric phÃ¹ há»£p nháº¥t pháº£n Ã¡nh tráº£i nghiá»‡m cá»§a HR.  
* **Äo lÆ°á»ng Pháº£n há»“i Äáº§u tiÃªn:** Sá»­ dá»¥ng **MRR** (Mean Reciprocal Rank) Ä‘á»ƒ Ä‘Ã¡nh giÃ¡ tá»‘c Ä‘á»™ há»‡ thá»‘ng cung cáº¥p káº¿t quáº£ Ä‘Ãºng Ä‘áº§u tiÃªn.43

### **5.2. Thiáº¿t láº­p Má»‘c ÄÃ¡nh giÃ¡ (Boundaries)**

Äá»ƒ Ä‘Ã¡nh giÃ¡ cÃ´ng báº±ng, há»‡ thá»‘ng cáº§n thiáº¿t láº­p cÃ¡c cá»™t má»‘c:

* **Lower Bound (Má»‘c cÆ¡ sá»Ÿ tá»‘i thiá»ƒu):**  
  Sá»­ dá»¥ng káº¿t quáº£ trá»±c tiáº¿p tá»« phÃ©p Ä‘o **Cosine Similarity thuáº§n tÃºy** báº±ng text-embedding-3-small trÃªn ná»™i dung vÄƒn báº£n gá»‘c, khÃ´ng sá»­ dá»¥ng bá»™ lá»c SQL, khÃ´ng chuáº©n hÃ³a ká»¹ nÄƒng. ÄÃ¢y lÃ  má»©c Ä‘iá»ƒm mÃ  há»‡ thá»‘ng FANG báº¯t buá»™c pháº£i vÆ°á»£t qua má»™t khoáº£ng cÃ¡ch xa Ä‘á»ƒ chá»©ng minh sá»± tá»“n táº¡i cá»§a há»‡ thá»‘ng lai (Hybrid) lÃ  há»£p lÃ½.  
* **Sanity Upper Reference (Má»‘c tráº§n tham chiáº¿u tham sá»‘ hÃ³a):** Viá»‡c táº¡o nhÃ£n thá»§ cÃ´ng (Human Annotation) trÃªn dá»¯ liá»‡u ATS quy mÃ´ lá»›n lÃ  báº¥t kháº£ thi. Äá»ƒ cÃ³ Ground Truth, FANG cáº§n sá»­ dá»¥ng phÆ°Æ¡ng phÃ¡p **Outcome-Grounded Benchmark** káº¿t há»£p **LLM-as-a-Judge**.5  
  * *Nguá»“n dá»¯ liá»‡u lá»‹ch sá»­:* CÃ¡c há»“ sÆ¡ á»©ng viÃªn trong báº£ng JOBAPPLICATION cÃ³ sá»± kiá»‡n tiáº¿n sÃ¢u vÃ o phá»ng váº¥n (INTERVIEWFEEDBACK) hoáº·c nháº­n thÆ° má»i lÃ m viá»‡c (OFFER) 1 sáº½ Ä‘Æ°á»£c tá»± Ä‘á»™ng gÃ¡n nhÃ£n TÆ°Æ¡ng quan cao (Relevance \= 2).  
  * *Nguá»“n dá»¯ liá»‡u Ä‘Ã¡nh giÃ¡ báº±ng AI:* Sá»­ dá»¥ng mÃ´ hÃ¬nh thuá»™c nhÃ³m Pro Tier (Gemini Pro hoáº·c GPT-5.4) 1 thÃ´ng qua kÄ© thuáº­t Prompt ká»¹ lÆ°á»¡ng, Ä‘Æ°á»£c cung cáº¥p toÃ n bá»™ JD vÃ  CV Ä‘á»ƒ cháº¥m Ä‘iá»ƒm má»©c Ä‘á»™ phÃ¹ há»£p tá»« 0-3 dá»±a trÃªn rubric kháº¯t khe. CÃ¡c nhÃ£n sinh ra bá»Ÿi LLM Pro sáº½ lÃ m má»‘c tham chiáº¿u "Tráº§n" Ä‘á»ƒ cÃ¡c mÃ´ hÃ¬nh Retrieval nhá» hÆ¡n (nhÆ° baseline hybrid) cá»‘ gáº¯ng tiáº¿p cáº­n.

### **5.3. NghiÃªn cá»©u Cáº¯t bá» (Ablation Study)**

Äá»ƒ tráº£ lá»i cÃ¢u há»i: *"Embedding hiá»‡n táº¡i Ä‘Ã³ng gÃ³p bao nhiÃªu % vÃ o Ä‘á»™ chÃ­nh xÃ¡c?"*, má»™t bÃ i kiá»ƒm tra Ablation (Cáº¯t bá») lÃ  báº¯t buá»™c.5

DÆ°á»›i Ä‘Ã¢y lÃ  ma tráº­n Ablation Study Ä‘Æ°á»£c Ä‘á» xuáº¥t váº­n hÃ nh trong há»‡ thá»‘ng FANG:

| Ká»‹ch báº£n Test (Runs) | Dense Embedding (text-embedding-3-small) | Metadata Filtering (SQL Lá»c Cá»©ng) | Sparse/Skill Matching (TÃ­nh Ä‘iá»ƒm Jaccard) | Má»¥c tiÃªu Quan sÃ¡t |
| :---- | :---- | :---- | :---- | :---- |
| **Run 0 (Lower Bound)** | Trá»ng sá»‘ \= 1.0 | KhÃ´ng Ã¡p dá»¥ng | Trá»ng sá»‘ \= 0.0 | Äo lÆ°á»ng nÄƒng lá»±c ngá»¯ nghÄ©a tráº§n trá»¥i. ÄÃ¡nh giÃ¡ má»©c Ä‘á»™ Semantic Hallucination. |
| **Run 1 (Heuristic Only)** | Trá»ng sá»‘ \= 0.0 | CÃ³ Ã¡p dá»¥ng | Trá»ng sá»‘ \= 1.0 | ÄÃ¡nh giÃ¡ nÄƒng lá»±c cá»§a kiáº¿n trÃºc DB quan há»‡ cÅ© (micareer\_lite\_db). |
| **Run 2 (Hybrid Basic)** | Trá»ng sá»‘ \= 0.5 | KhÃ´ng Ã¡p dá»¥ng | Trá»ng sá»‘ \= 0.5 | Kiá»ƒm tra xem sá»± káº¿t há»£p ngá»¯ nghÄ©a vÃ  tá»« khÃ³a cÃ³ cáº£i thiá»‡n NDCG khÃ´ng khi bá» qua rÃ ng buá»™c cá»©ng. |
| **Run 3 (Hybrid Full \- Äá» xuáº¥t)** | Trá»ng sá»‘ \= ![][image5] | CÃ³ Ã¡p dá»¥ng | Trá»ng sá»‘ \= ![][image6] | TÃ¬m ra há»‡ sá»‘ calibration tá»‘t nháº¥t. XÃ¡c nháº­n Uplift cá»§a toÃ n bá»™ há»‡ thá»‘ng. |

**TiÃªu chÃ­ quyáº¿t Ä‘á»‹nh:** Náº¿u chÃªnh lá»‡ch ![][image9] giá»¯a **Run 3** vÃ  **Run 1** cá»±c ká»³ tháº¥p (vÃ­ dá»¥ \< 2-3%), Ä‘iá»u Ä‘Ã³ cÃ³ nghÄ©a mÃ´ hÃ¬nh embedding hiá»‡n táº¡i thá»±c sá»± lÃ  Bottleneck vÃ  khÃ´ng mang láº¡i kháº£ nÄƒng náº¯m báº¯t bá»‘i cáº£nh nÃ o hÆ¡n viá»‡c Ä‘áº¿m tá»« khÃ³a thÃ´ng thÆ°á»ng. Trong trÆ°á»ng há»£p nÃ y, Ä‘á» xuáº¥t nÃ¢ng cáº¥p mÃ´ hÃ¬nh embedding hoáº·c huáº¥n luyá»‡n tinh chá»‰nh (Fine-tuning) báº±ng phÆ°Æ¡ng phÃ¡p Contrastive Learning sáº½ Ä‘Æ°á»£c kÃ­ch hoáº¡t.5

## **6\. Chiáº¿n lÆ°á»£c Má»Ÿ rá»™ng Dá»¯ liá»‡u Tá»•ng há»£p (Synthetic ATS Data) vÃ  Quality Gates**

Äá»ƒ váº­n hÃ nh giao thá»©c Ä‘Ã¡nh giÃ¡ ngoáº¡i tuyáº¿n trÃªn má»™t cÃ¡ch hiá»‡u quáº£, há»‡ thá»‘ng gáº·p pháº£i rÃ o cáº£n vá» tÃ­nh báº£o máº­t dá»¯ liá»‡u vÃ  sá»± máº¥t cÃ¢n báº±ng nhÃ³m (class imbalance) trong dá»¯ liá»‡u tháº­t. Chiáº¿n lÆ°á»£c **sinh dá»¯ liá»‡u tá»•ng há»£p (Synthetic Data Generation)** á»Ÿ má»©c thá»±c táº¿ lÃ  chÃ¬a khÃ³a giáº£i quyáº¿t váº¥n Ä‘á» nÃ y, Ä‘áº·c biá»‡t Ä‘á»ƒ táº¡o ra cÃ¡c trÆ°á»ng há»£p "Hard Negatives" (Gáº§n Ä‘Ãºng nhÆ°ng sai báº£n cháº¥t).39

### **6.1. PhÆ°Æ¡ng phÃ¡p Sinh CV vÃ  JD Quy mÃ´ lá»›n**

Sá»­ dá»¥ng nÄƒng lá»±c cá»§a há»‡ thá»‘ng FANG hiá»‡n hÃ nh (cÃ¡c mÃ´ hÃ¬nh LLM thuá»™c Lite/Pro Tiers) 1 Ä‘á»ƒ tá»± Ä‘á»™ng hÃ³a quÃ¡ trÃ¬nh sinh dá»¯ liá»‡u:

1. **Háº¡t giá»‘ng Dá»¯ liá»‡u (Seed Data):** Láº¥y máº«u ngáº«u nhiÃªn vÃ  áº©n danh hÃ³a (de-identify) má»™t táº­p há»£p nhá» cÃ¡c JD vÃ  CV thá»±c táº¿ tá»« báº£ng JOBPOSTING vÃ  CVPARSED.1  
2. **Sinh máº«u TÃ­ch cá»±c (Positive Augmentation):** DÃ¹ng LLM viáº¿t láº¡i (paraphrase) cÃ¡c CV sao cho chÃºng thay Ä‘á»•i vá» máº·t tá»« vá»±ng, cáº¥u trÃºc trÃ¬nh bÃ y, thá»© tá»± cÃ¡c pháº§n (Ä‘á»ƒ mÃ´ phá»ng cÃ¡c format PDF khÃ¡c nhau) nhÆ°ng váº«n giá»¯ nguyÃªn Ã½ nghÄ©a chuyÃªn mÃ´n (Semantic Fidelity) nháº±m khá»›p hoÃ n háº£o vá»›i má»™t JD.39  
3. **Sinh máº«u Äá»‘i nghá»‹ch KhÃ³ (Hard Negative Mining/Generation):** ÄÃ¢y lÃ  bÆ°á»›c quan trá»ng nháº¥t Ä‘á»ƒ rÃ¨n luyá»‡n baseline.9 YÃªu cáº§u LLM táº¡o ra cÃ¡c CV:  
   * Chia sáº» Ä‘áº¿n 80% tá»« vá»±ng vá»›i JD (vÃ­ dá»¥ dÃ¹ng chung cÃ¡c tá»« quáº£n lÃ½, láº­p trÃ¬nh, kiá»ƒm thá»­).  
   * NhÆ°ng thay Ä‘á»•i má»™t cÃ´ng nghá»‡ cá»‘t lÃµi (Java thÃ nh C\#) hoáº·c háº¡ tháº¥p sá»‘ nÄƒm kinh nghiá»‡m xuá»‘ng dÆ°á»›i má»©c yÃªu cáº§u. CÃ¡c há»“ sÆ¡ nÃ y sáº½ Ä‘Æ°á»£c gÃ¡n nhÃ£n Relevance \= 0, buá»™c há»‡ thá»‘ng Linear Scoring há»c cÃ¡ch trá»« Ä‘iá»ƒm thÃ­ch Ä‘Ã¡ng.

### **6.2. Cá»•ng Cháº¥t lÆ°á»£ng Dá»¯ liá»‡u (Data Quality Gates) & Consistency Checks**

KhÃ´ng thá»ƒ Ä‘Æ°a dá»¯ liá»‡u LLM sinh ra trá»±c tiáº¿p vÃ o Ä‘Ã¡nh giÃ¡ mÃ  khÃ´ng cÃ³ cÆ¡ cháº¿ kiá»ƒm duyá»‡t. FANG cáº§n tÃ­ch há»£p cÃ¡c quy trÃ¬nh Quality Gates kháº¯t khe 1:

* **Structural Consistency Check (Kiá»ƒm tra TÃ­nh Nháº¥t quÃ¡n Cáº¥u trÃºc):** Má»i CV tá»•ng há»£p pháº£i Ä‘i qua bá»™ Parser 5 táº§ng hiá»‡n táº¡i cá»§a FANG. Náº¿u Parser khÃ´ng thá»ƒ trÃ­ch xuáº¥t Ä‘Æ°á»£c rawText length hoáº·c cÃ¡c section signals há»£p lá»‡ theo rule deterministic, CV tá»•ng há»£p Ä‘Ã³ sáº½ bá»‹ loáº¡i bá».1  
* **Temporal Consistency (Kiá»ƒm tra Nháº¥t quÃ¡n Thá»i gian):** Viáº¿t script Python Ä‘á»ƒ kiá»ƒm tra logic thá»i gian (VÃ­ dá»¥: NÄƒm tá»‘t nghiá»‡p Ä‘áº¡i há»c trá»« Ä‘i nÄƒm sinh pháº£i há»£p lÃ½, sá»‘ nÄƒm lÃ m viá»‡c trong CV pháº£i tá»•ng hÃ²a tÆ°Æ¡ng Ä‘Æ°Æ¡ng vá»›i CANDIDATE.expyears 1).  
* **Data Leakage/Contamination Check:** Äáº£m báº£o ráº±ng táº­p dá»¯ liá»‡u dÃ¹ng Ä‘á»ƒ cháº¡y text-embedding-3-small lÃ m tham chiáº¿u Ä‘Ã¡nh giÃ¡ pháº£i hoÃ n toÃ n cÃ´ láº­p vá»›i táº­p dá»¯ liá»‡u (Prompts) Ä‘Æ°a vÃ o LLM Ä‘á»ƒ sinh dá»¯ liá»‡u. KhÃ´ng dÃ¹ng chÃ­nh LLM Ä‘Ã¡nh giÃ¡ (LLM-as-a-judge) Ä‘á»ƒ sinh dá»¯ liá»‡u tá»•ng há»£p á»Ÿ cÃ¹ng má»™t tham sá»‘ nhiá»‡t Ä‘á»™ (temperature) Ä‘á»ƒ trÃ¡nh thiÃªn vá»‹ thuáº­t toÃ¡n (algorithmic bias).

## **7\. Khuyáº¿n nghá»‹ vÃ  Tá»•ng káº¿t Chiáº¿n lÆ°á»£c**

NghiÃªn cá»©u káº¿t luáº­n ráº±ng cáº¥u trÃºc lÆ°u trá»¯ vÃ  nhÃºng vector hiá»‡n táº¡i cá»§a FANG v2 lÃ  má»™t bá»‡ phÃ³ng vá»¯ng cháº¯c vÃ  **khÃ´ng nÃªn bá»‹ thay tháº¿ trong giai Ä‘oáº¡n nÃ y**. CÃ¡c Ä‘iá»ƒm ngháº½n vá» ngá»¯ nghÄ©a vÃ  tÃ­nh báº¥t Ä‘á»‘i xá»©ng trong tÃ¬m kiáº¿m cÃ³ thá»ƒ Ä‘Æ°á»£c giáº£i quyáº¿t thÃ´ng qua ká»¹ thuáº­t toÃ¡n há»c táº¡i lá»›p truy xuáº¥t.

DÆ°á»›i Ä‘Ã¢y lÃ  báº£ng xáº¿p háº¡ng Æ°u tiÃªn cÃ¡c quyáº¿t Ä‘á»‹nh ká»¹ thuáº­t cáº§n thá»±c thi ngay, thá»a mÃ£n Ä‘iá»u kiá»‡n triá»ƒn khai nhanh vÃ  kiá»ƒm chá»©ng ngoáº¡i tuyáº¿n (Offline Evaluation) 5:

1. **Thiáº¿t láº­p Baseline Há»‡ thá»‘ng (Æ¯u tiÃªn Cao nháº¥t):** Triá»ƒn khai ngay láº­p tá»©c phÆ°Æ¡ng phÃ¡p **Hybrid Search káº¿t há»£p Linear Scoring**. Äiá»ƒm sá»‘ cuá»‘i cÃ¹ng sáº½ lÃ  sá»± káº¿t há»£p cÃ³ trá»ng sá»‘ giá»¯a ![][image10] cá»§a halfvec(1024) 1 tá»« PostgreSQL vÃ  Ä‘iá»ƒm Jaccard cá»§a CANDIDATESKILL / JOBREQUIREMENT 1, Ä‘Æ°á»£c lá»c trÆ°á»›c (Hard Filter) báº±ng SQL thÃ´ng qua sá»‘ nÄƒm kinh nghiá»‡m vÃ  Ä‘á»‹a lÃ½. KhÃ´ng sá»­ dá»¥ng Reciprocal Rank Fusion (RRF) do báº£n cháº¥t dá»… che láº¥p cÃ¡c lá»—i sai ká»¹ nÄƒng nghiÃªm trá»ng.  
2. **TÃ¡ch biá»‡t Luá»“ng Äá»‘i khá»›p (Æ¯u tiÃªn Cao):** XÃ¢y dá»±ng hai hÃ m Linear Scoring riÃªng biá»‡t:  
   * *Candidate ![][image3] Job:* Ná»›i lá»ng cÃ¡c bá»™ lá»c SQL thÃ nh Ä‘iá»ƒm trá»« (soft penalty) Ä‘á»ƒ tÄƒng Recall vÃ  tÃ­nh Ä‘a dáº¡ng.  
   * *Job ![][image3] Candidate:* Sá»­ dá»¥ng cÃ¡c bá»™ lá»c cá»©ng kháº¯t khe báº±ng SQL trÆ°á»›c khi thá»±c hiá»‡n Vector Search Ä‘á»ƒ tá»‘i Ä‘a hÃ³a Precision.  
3. **Khá»Ÿi Ä‘á»™ng Giao thá»©c PJB (Person-Job Benchmark) Ná»™i bá»™ (Æ¯u tiÃªn Trung bÃ¬nh):** Thiáº¿t láº­p ká»‹ch báº£n Ablation Study trÃªn má»™t táº­p dá»¯ liá»‡u 10,000 cáº·p CV-JD (Ä‘Æ°á»£c trá»™n giá»¯a dá»¯ liá»‡u tháº­t vÃ  dá»¯ liá»‡u tá»•ng há»£p cÃ³ kiá»ƒm soÃ¡t báº±ng Quality Gate). Sá»­ dá»¥ng NDCG@10 vÃ  Recall@50 lÃ m bá»™ Ä‘Ã´i chá»‰ sá»‘ Ä‘á»‹nh hÆ°á»›ng.  
4. **Báº£o toÃ n Háº¡ táº§ng text-embedding-3-small:** Giá»¯ nguyÃªn quy trÃ¬nh cáº¥u trÃºc Parser 5 táº§ng, mÃ´ hÃ¬nh nhÃºng vÃ  báº£ng lÆ°u trá»¯ halfvec(1024). Viá»‡c chuyá»ƒn Ä‘á»•i sang mÃ´ hÃ¬nh tinh chá»‰nh miá»n Ä‘áº·c thÃ¹ (Domain-adapted LLMs) hay Cross-Encoders phá»©c táº¡p chá»‰ Ä‘Æ°á»£c khá»Ÿi Ä‘á»™ng náº¿u vÃ  chá»‰ náº¿u bÃ i kiá»ƒm tra Ablation cho tháº¥y mÃ´ hÃ¬nh nhÃºng hiá»‡n táº¡i khÃ´ng mang láº¡i má»©c tÄƒng trÆ°á»Ÿng ![][image11] so vá»›i viá»‡c chá»‰ dÃ¹ng Metadata SQL.

HÆ°á»›ng Ä‘i nÃ y tá»‘i Ä‘a hÃ³a cÃ¡c thÃ nh pháº§n Ä‘Ã£ cÃ³ sáºµn táº¡i AI Core FANG, Ä‘áº£m báº£o tiáº¿t kiá»‡m chi phÃ­ tÃ­nh toÃ¡n API ($0.02/1M token 34), Ä‘á»“ng thá»i Ã¡p Ä‘áº·t má»™t khung quáº£n trá»‹ cháº¥t lÆ°á»£ng cá»±c ká»³ nghiÃªm ngáº·t Ä‘á»‘i vá»›i há»‡ thá»‘ng xáº¿p háº¡ng tuyá»ƒn dá»¥ng. CÃ¡c khuyáº¿n nghá»‹ trong bÃ¡o cÃ¡o nÃ y hoÃ n toÃ n kháº£ thi Ä‘á»ƒ thá»±c hiá»‡n ngay láº­p tá»©c, Ä‘Ã³ng vai trÃ² nhÆ° má»™t cá»™t má»‘c cÆ¡ sá»Ÿ (gold standard baseline) vá»¯ng cháº¯c, lÃ m bá»‡ phÃ³ng cho cÃ¡c cá»¥m nghiÃªn cá»©u vÃ  tinh chá»‰nh (tuning) tiáº¿p theo.

#### **Nguá»“n trÃ­ch dáº«n**

1. schema\_ai\_core.sql  
2. Synapse: Evolving Job-Person Fit with Explainable Two-phase Retrieval and LLM-guided Genetic Resume Optimization \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2604.02539v1](https://arxiv.org/html/2604.02539v1)  
3. Fairness of recommender systems in the recruitment domain: an analysis from technical and legal perspectives \- PMC, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10587596/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10587596/)  
4. Fairness in AI-Driven Recruitment: Challenges, Metrics, Methods, and Future Directions, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2405.19699v3](https://arxiv.org/html/2405.19699v3)  
5. PJB: A Reasoning-Aware Benchmark for Person-Job Retrieval \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2603.17386](https://arxiv.org/html/2603.17386)  
6. PJB: A Reasoning-Aware Benchmark for Person-Job Retrieval \- WisPaper, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.wispaper.ai/en/blog/reasoning-aware-benchmark-person-job-retrieval-20260320/zho](https://www.wispaper.ai/en/blog/reasoning-aware-benchmark-person-job-retrieval-20260320/zho)  
7. How AI Is Replacing Traditional Hiring \-And the Tools Smart Recruiters Are Already Using in 2026 | by Klizo Solutions Pvt. Ltd. \- Medium, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://medium.com/@klizosolutions/how-ai-is-replacing-traditional-hiring-and-the-tools-smart-recruiters-are-already-using-in-2026-21b36f40454b](https://medium.com/@klizosolutions/how-ai-is-replacing-traditional-hiring-and-the-tools-smart-recruiters-are-already-using-in-2026-21b36f40454b)  
8. Why generic embeddings fail for workforce decisions | Agentic HR Academy \- Gloat, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://gloat.com/academy/why-generic-embeddings-fail-workforce/](https://gloat.com/academy/why-generic-embeddings-fail-workforce/)  
9. CONFIT V2: Improving Resume-Job Matching using Hypothetical Resume Embedding and Runner-Up Hard-Negative Mining \- ACL Anthology, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://aclanthology.org/2025.findings-acl.661.pdf](https://aclanthology.org/2025.findings-acl.661.pdf)  
10. ConFit v2: Improving Resume-Job Matching using Hypothetical Resume Embedding and Runner-Up Hard-Negative Mining \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2502.12361v1](https://arxiv.org/html/2502.12361v1)  
11. Algorithms risk perpetuating bias in hiring. How can employers use them to make hiring more inclusive? | Urban Institute, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.urban.org/urban-wire/algorithms-risk-perpetuating-bias-hiring-how-can-employers-use-them-make-hiring-more-inclusive](https://www.urban.org/urban-wire/algorithms-risk-perpetuating-bias-hiring-how-can-employers-use-them-make-hiring-more-inclusive)  
12. AI-assisted recruitment is biased. Here's how to make it more fair | World Economic Forum, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.weforum.org/stories/2019/05/ai-assisted-recruitment-is-biased-heres-how-to-beat-it/](https://www.weforum.org/stories/2019/05/ai-assisted-recruitment-is-biased-heres-how-to-beat-it/)  
13. The Vector Bottleneck: Limitations of Embedding-Based Retrieval \- Shaped.ai, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.shaped.ai/blog/the-vector-bottleneck-limitations-of-embedding-based-retrieval](https://www.shaped.ai/blog/the-vector-bottleneck-limitations-of-embedding-based-retrieval)  
14. Hyper-Relevant Semantic Hiring with Vector Search & RAG \- V2Solutions, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.v2solutions.com/blogs/semantic-hiring-vector-search-rag/](https://www.v2solutions.com/blogs/semantic-hiring-vector-search-rag/)  
15. How does vector search compare to hybrid search approaches? \- Milvus, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://milvus.io/ai-quick-reference/how-does-vector-search-compare-to-hybrid-search-approaches](https://milvus.io/ai-quick-reference/how-does-vector-search-compare-to-hybrid-search-approaches)  
16. A Comprehensive Hybrid Search Guide | Elastic, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.elastic.co/what-is/hybrid-search](https://www.elastic.co/what-is/hybrid-search)  
17. Hybrid Search Fusion Ranking \- Salesforce Help, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://help.salesforce.com/s/articleView?id=data.c360\_a\_hybridsearch\_fusion\_ranking.htm\&language=en\_US\&type=5](https://help.salesforce.com/s/articleView?id=data.c360_a_hybridsearch_fusion_ranking.htm&language=en_US&type=5)  
18. Elastic linear retriever for hybrid search: introduction & config \- Elasticsearch Labs, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.elastic.co/search-labs/blog/linear-retriever-hybrid-search](https://www.elastic.co/search-labs/blog/linear-retriever-hybrid-search)  
19. Relevance scoring in hybrid search using Reciprocal Rank Fusion (RRF) \- Microsoft Learn, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)  
20. Understand Hybrid Search \- Oracle Help Center, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/understand-hybrid-search.html](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/understand-hybrid-search.html)  
21. Reciprocal Rank Fusion and Relative Score Fusion: Classic Hybrid Search Techniques | by MongoDB \- Medium, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://medium.com/mongodb/reciprocal-rank-fusion-and-relative-score-fusion-classic-hybrid-search-techniques-3bf91008b81d](https://medium.com/mongodb/reciprocal-rank-fusion-and-relative-score-fusion-classic-hybrid-search-techniques-3bf91008b81d)  
22. Real-Time Hybrid Search Using RRF \- Spice AI, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://spice.ai/blog/real-time-hybrid-search-using-rrf](https://spice.ai/blog/real-time-hybrid-search-using-rrf)  
23. Resume2Vec: Transforming Applicant Tracking Systems with Intelligent Resume Embeddings for Precise Candidate Matching \- MDPI, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.mdpi.com/2079-9292/14/4/794](https://www.mdpi.com/2079-9292/14/4/794)  
24. Building a Job Description to Resume Matcher using Natural Language Processing, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://kartikmadan11.medium.com/building-a-job-description-to-resume-matcher-using-natural-language-processing-5a4f5181cfe4](https://kartikmadan11.medium.com/building-a-job-description-to-resume-matcher-using-natural-language-processing-5a4f5181cfe4)  
25. AI-Driven Resume Analysis and Enhancement Using Semantic Modeling and Large Language Feedback Loops \- ACL Anthology, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://aclanthology.org/2025.clicit-1.51.pdf](https://aclanthology.org/2025.clicit-1.51.pdf)  
26. Combining Embeddings and Domain Knowledge for Job Posting Duplicate Detection \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2406.06257v1](https://arxiv.org/html/2406.06257v1)  
27. VietJobs: A Vietnamese Job Advertisement Dataset \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2603.05262v1](https://arxiv.org/html/2603.05262v1)  
28. VietJobs: A Vietnamese Job Advertisement Dataset \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/pdf/2603.05262](https://arxiv.org/pdf/2603.05262)  
29. Deep Learning for Categorizing Job Titles \- Textkernel, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.textkernel.com/learn-support/blog/deep-learning-for-categorizing-job-titles/](https://www.textkernel.com/learn-support/blog/deep-learning-for-categorizing-job-titles/)  
30. Extracting position titles from unstructured historical job advertisements \- ACL Anthology, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://aclanthology.org/2024.nlp4dh-1.8.pdf](https://aclanthology.org/2024.nlp4dh-1.8.pdf)  
31. SAGE: A Realistic Benchmark for Semantic Understanding \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2509.21310v1](https://arxiv.org/html/2509.21310v1)  
32. Hanoi to tap into AI to analyze labor market data \- VnEconomy, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://en.vneconomy.vn/hanoi-to-tap-into-ai-to-analyze-labor-market-data.htm](https://en.vneconomy.vn/hanoi-to-tap-into-ai-to-analyze-labor-market-data.htm)  
33. Embeddings FAQ \- OpenAI Help Center, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://help.openai.com/en/articles/6824809-embeddings-faq](https://help.openai.com/en/articles/6824809-embeddings-faq)  
34. text-embedding-3-small Model | OpenAI API, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://developers.openai.com/api/docs/models/text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small)  
35. text-embedding-3-small: High-Quality Embeddings at Scale \- PromptLayer Blog, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://blog.promptlayer.com/text-embedding-3-small-high-quality-embeddings-at-scale/](https://blog.promptlayer.com/text-embedding-3-small-high-quality-embeddings-at-scale/)  
36. Analyzing Performance Gains in OpenAI's Text-Embedding-3-Small \- TiDB, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.pingcap.com/article/analyzing-performance-gains-in-openais-text-embedding-3-small/](https://www.pingcap.com/article/analyzing-performance-gains-in-openais-text-embedding-3-small/)  
37. Evaluating OpenAI's new embedding models with Lantern and Parea AI, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://lantern.dev/blog/evaluating](https://lantern.dev/blog/evaluating)  
38. JobMatchAI An Intelligent Job Matching Platform Using Knowledge Graphs, Semantic Search and Explainable AI Website Installation Package Demo Video \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2603.14558v2](https://arxiv.org/html/2603.14558v2)  
39. Mira-Embeddings-V1: Domain-Adapted Semantic Reranking for Recruitment via LLM-Synthesized Data \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2604.17738v1](https://arxiv.org/html/2604.17738v1)  
40. On the Embedding Collapse When Scaling Up Recommendation Models \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2310.04400v2](https://arxiv.org/html/2310.04400v2)  
41. How do you increase accuracy in CV â†” Job matching with embeddings? : r/Rag \- Reddit, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1n3t15r/how\_do\_you\_increase\_accuracy\_in\_cv\_job\_matching/](https://www.reddit.com/r/Rag/comments/1n3t15r/how_do_you_increase_accuracy_in_cv_job_matching/)  
42. The Hidden Problem in Vector Search: You're Measuring Similarity, Not Relevance : r/Rag \- Reddit, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1pcgrnj/the\_hidden\_problem\_in\_vector\_search\_youre/](https://www.reddit.com/r/Rag/comments/1pcgrnj/the_hidden_problem_in_vector_search_youre/)  
43. Evaluation Metrics for Search and Recommendation Systems \- Weaviate, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://weaviate.io/blog/retrieval-evaluation-metrics](https://weaviate.io/blog/retrieval-evaluation-metrics)  
44. A Practical Guide to Recall, Precision, and NDCG \- Edge AI and Vision Alliance, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.edge-ai-vision.com/2026/02/a-practical-guide-to-recall-precision-and-ndcg/](https://www.edge-ai-vision.com/2026/02/a-practical-guide-to-recall-precision-and-ndcg/)  
45. Normalized Discounted Cumulative Gain (NDCG) explained \- Evidently AI, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/ndcg-metric](https://www.evidentlyai.com/ranking-metrics/ndcg-metric)  
46. 10 metrics to evaluate recommender and ranking systems \- Evidently AI, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems](https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems)  
47. Ranking Evaluation Metrics for Recommender Systems | Towards Data Science, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://towardsdatascience.com/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54/](https://towardsdatascience.com/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54/)  
48. Towards Comparing Recommendation to Multiple-Query Search Sessions for Talent Search \- Aalborg Universitets forskningsportal, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://vbn.aau.dk/files/517887376/Open\_Access\_Article.pdf](https://vbn.aau.dk/files/517887376/Open_Access_Article.pdf)  
49. A Theoretical Analysis of NDCG Type Ranking Measures | Request PDF \- ResearchGate, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.researchgate.net/publication/236274361\_A\_Theoretical\_Analysis\_of\_NDCG\_Type\_Ranking\_Measures](https://www.researchgate.net/publication/236274361_A_Theoretical_Analysis_of_NDCG_Type_Ranking_Measures)  
50. Evaluating recommendation systems (mAP, MMR, NDCG) \- Shaped.ai, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg](https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg)  
51. Ranking Evaluation Metrics for Recommender Systems | by Benjamin Wang \- Medium, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54](https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54)  
52. VN-MTEB: Vietnamese Massive Text Embedding ... \- ACL Anthology, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://aclanthology.org/2026.findings-eacl.86.pdf](https://aclanthology.org/2026.findings-eacl.86.pdf)  
53. RecruitBench: An Outcome-Grounded Benchmark for Evaluating AI Recruiting Systems \- Stanford University, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://cs191w.stanford.edu/projects/Winter2026/\_Aditya\_\_\_Sood\_.pdf](https://cs191w.stanford.edu/projects/Winter2026/_Aditya___Sood_.pdf)  
54. Concept Embedding Models: Beyond the Accuracy-Explainability Trade-Off, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://proceedings.neurips.cc/paper\_files/paper/2022/file/867c06823281e506e8059f5c13a57f75-Paper-Conference.pdf](https://proceedings.neurips.cc/paper_files/paper/2022/file/867c06823281e506e8059f5c13a57f75-Paper-Conference.pdf)  
55. Innovative Recommendation Applications Using Two Tower Embeddings at Uber, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.uber.com/us/en/blog/innovative-recommendation-applications-using-two-tower-embeddings/](https://www.uber.com/us/en/blog/innovative-recommendation-applications-using-two-tower-embeddings/)  
56. Inferring Complementary and Substitutable Products Based on Knowledge Graph Reasoning \- MDPI, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://www.mdpi.com/2227-7390/11/22/4709](https://www.mdpi.com/2227-7390/11/22/4709)  
57. Lessons learned on information retrieval in electronic health records: a comparison of embedding models and pooling strategies \- PMC, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11756698/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11756698/)  
58. Predictive modeling of clinical trial terminations using feature engineering and embedding learning \- PMC, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC7876037/](https://pmc.ncbi.nlm.nih.gov/articles/PMC7876037/)  
59. VN-MTEB: Vietnamese Massive Text Embedding Benchmark \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2507.21500v1](https://arxiv.org/html/2507.21500v1)  
60. AgentIR: Reasoning-Aware Retrival for Deep Research Agents \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2603.04384v1](https://arxiv.org/html/2603.04384v1)  
61. LLMs are Also Effective Embedding Models: An In-depth Overview \- arXiv, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://arxiv.org/html/2412.12591v1](https://arxiv.org/html/2412.12591v1)  
62. Best Embedding Models 2026: Benchmarks, Pricing ($0.02-$0.18/1M) \- PE Collective, truy cáº­p vÃ o thÃ¡ng 4 23, 2026, [https://pecollective.com/tools/best-embedding-models/](https://pecollective.com/tools/best-embedding-models/)

[image1]: images/NMAIex_1/image1.png

[image2]: images/NMAIex_1/image2.png

[image3]: images/NMAIex_1/image3.png

[image4]: images/NMAIex_1/image4.png

[image5]: images/NMAIex_1/image5.png

[image6]: images/NMAIex_1/image6.png

[image7]: images/NMAIex_1/image7.png

[image8]: images/NMAIex_1/image8.png

[image9]: images/NMAIex_1/image9.png

[image10]: images/NMAIex_1/image10.png

[image11]: images/NMAIex_1/image11.png

