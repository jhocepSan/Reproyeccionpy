import os, calendar, logging
from datetime import datetime, timedelta
import rasterio
from rasterio.merge import merge
import numpy as np
import re

# --- Configuración de Logging (Misma lógica que tenías) ---
class InfoFilter(logging.Filter):
    def filter(self, record): return record.levelno < logging.ERROR

logger = logging.getLogger("MiLogger")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')

def setup_loggers():
    h1 = logging.FileHandler("sqlFechas_swc_cmpc26.log", mode="a", encoding="utf-8")
    h1.setLevel(logging.DEBUG)
    h1.addFilter(InfoFilter())
    h2 = logging.FileHandler("sqlCalculo_swc_cmpc26.log", mode="a", encoding="utf-8")
    h2.setLevel(logging.ERROR)
    for h in [h1, h2]:
        h.setFormatter(formatter)
        logger.addHandler(h)

setup_loggers()
carpetas_invalidas={'8757fa22-fbf5-4a42-b209-59ab269737ef','003c0c07-65d9-4963-ba6b-6534a5c4c9d8', '00468679-ddd8-423e-bb5a-03386d134adc', '0111e41c-18f6-42d2-a8f2-e7030e42b081', '0265d163-6b1e-4bf3-a598-4471a4853234', '0280fcc4-a0db-42bf-9c3f-f9d2a58a0e55', '045bddc0-ed1a-497d-9ddf-e9873c5a46dd', '04b57ab4-eacb-4a29-bca9-e47ed5711b7e', '056445eb-7cde-47fa-9bdb-f61fa77749ca', '05654ce5-d291-44da-a71c-dbe54c71acf4', '057751c8-1319-44f1-89e5-8d4623afa05d', '059cb826-2103-44bf-9745-75c96a45b3ff', '05d0f943-86db-4f12-81c6-c652327901be', '05ff352f-a6cb-4aaf-afc5-3ecb87fe9e9b', '063508a0-20cf-451e-ae1b-0c8df26ab99d', '06c73106-ae19-4f1f-8a25-79915ec8438b', '075e07ba-1aeb-41eb-8fdf-1086d6dc1a16', '07662db8-0c5b-4e92-819a-1f180a23f6df', '078b6a67-814e-4719-81ad-a8c7c129949a', '079b635a-6ab5-4ed7-a2cf-57b4a0c13ce4', '083ddcfd-d9d9-4529-a0e6-2565207d878f', '0b8f4cda-faa0-4d8b-87ca-4ffc682ca2d6', '0ba559f1-8f4a-417a-b3cc-17043c3a0063', '0bbb8c0b-ebc0-4a40-b0f9-cbdfa1a990fe', '0cd06594-e0f9-402e-bbe3-f59ddc046794', '0d7ef8b0-d978-4b84-a967-c8a9e2804b73', '0e0cc117-06f1-47b5-b506-778b69509252', '0e46ca27-2f6e-4e4d-982d-5b93dcfd7bb3', '0ed470fd-7cdc-4fbd-9759-fe1ad5b6e487', '0ed98ff9-2f50-44a0-a94c-622abbecc4c9', '0f868851-ee69-4e6c-bbd5-ee6840cda17c', '1019017e-f9c1-4959-8f63-346873c5f01d', '10674df8-a3d3-4a6c-96f2-1301776e831b', '10c60313-2e9c-4467-ab42-343bf22e9589', '11474e00-1d1a-4a0c-b973-c403066946c9', '11555a0b-c84f-4315-8607-029484cddaec', '11851982-f8c0-4bd5-b44b-e6646158f84b', '12d2827e-7748-4f92-9d89-527f3228d3bd', '12ea0eda-9471-4cea-bb73-aa62d2482350', '13289a62-7b8c-4e72-9069-8845bb7ac20d', '1456524c-6b09-4914-9f3f-fa1173884ce7', '1476586c-54a7-4ef6-8f6e-1ec3f3220445', '149b521a-9306-4fc6-b222-748b9873f5e9', '151d7b89-a2f5-4c39-aa6e-a9703fc4b69c', '159fc1e2-af85-48e3-becc-819bea18b562', '161b1631-37b7-419d-a87e-2c5a8935124e', '17563eee-f86d-4eca-897c-58f161bb5aa0', '178dd7a2-36b1-4a02-aca9-0ffa3cf785a8', '184c728f-1865-48c6-ad61-358b278aa4ae', '18c3f974-c335-422c-aa31-3ee9896fa472', '18c8ac3b-62fb-4e23-83a2-11f41237cf71', '19580de8-186c-4124-82d1-ab42d4f4479f', '19a051c3-cf7b-4b7e-bfbf-67bc6e39e5b1', '19c62b4b-909b-4ca4-872e-d131b0042c8c', '1a051f31-0ce4-4090-a1db-0e3079ee3b34', '1a1fb85f-eb52-496a-9713-b503475193f3', '1a79eb06-6d86-49dc-a53d-3ede75ba035e', '1b18254c-da4f-4470-b363-2fa547b3b154', '1b769f67-f410-40f9-871b-4fa1bcc5098e', '1c0663fe-5c37-4b67-8acd-13653cb0d64e', '1c49e34a-a7d2-4122-b2a1-355ed35623c4', '1cee279e-a1f5-4b2e-aea3-d93be502018e', '1db5e42d-b9f8-4af4-98c6-51b2ec3822b7', '1e866fb8-bf06-4469-bc58-fcc4d875efaa', '1f3cbadd-9801-42e1-95c8-d664d0fe0a62', '1ff5333c-2009-4423-9843-20231f2dd449', '204b8ad1-2b3c-4f45-a5e9-b11165c36c10', '205dde43-1eb8-4924-a1be-ca52da5d9146', '211b9cfa-f769-45a1-a483-0c5a7e788041', '2141ec96-3de5-4352-abcb-1d3ce843c7c1', '21752142-ab3f-45b3-b64e-faae748b69f8', '21e7d1c6-b193-4cfd-97bf-f39f6144368b', '227ed2d9-031b-41e1-ab7f-6504a0383a02', '22839d0b-10a9-4201-9211-eab7512e0786', '232e2711-fd85-43ef-8cb6-f4517a0039f5', '2378b483-843b-4f5e-8568-86b340d8740a', '23ac73bd-f334-47c3-8384-d75bbe4f27bf', '23fde770-d340-4fa1-9883-ee1f8fe825be', '2402076b-301c-4464-89b1-77b6a2949c85', '24500ee2-9fa7-4f77-8f2f-cec3843a8462', '2597fc88-d6fa-4be8-a209-873786e9f2a6', '2600cc3a-4ef6-4142-99f3-bc12738e686c', '266dece8-a25f-4384-989b-44c7069ef1f1', '26de80c8-7faf-4403-a637-04c7f642e7ca', '27323bac-877a-4eca-b242-ab737663f39a', '2764dace-c248-4d2d-8571-cfb756dd9046', '27fda556-7a4d-43eb-8b68-9291d5c86bfe', '282b0fff-cd8f-42d5-a438-cf6435d3ea41', '2935d912-d1d7-4172-9393-ace872a57fb1', '29d8da5d-b54f-47db-aadb-96398bbdad76', '29fa6ac0-08a8-4691-a04d-70b4ea27842c', '2a445ffe-477a-408c-9b26-583a1b79bcf9', '2a4517e4-962c-4c32-a736-44f35c5944d2', '2b57360b-1b57-4432-8a28-203e914c9d48', '2cf4ec68-570e-4891-b495-d3a09c4068e3', '2e5ab78d-d2cf-4050-84ea-f3d54bb9d044', '2ecdef33-a47b-48a8-8ed4-2b74dbfde743', '2ee0e19b-24a1-42ef-b9db-dd1361f6b778', '2f35490f-1427-4af1-b02f-5919d979ba35', '307268d0-7e0a-4e12-8b14-2bc3e6ac0762', '30ece8ca-1675-411b-8904-02930daa9276', '3115e931-5ecd-4fd5-b37c-04c2dc156b2a', '3117dc65-04bf-40a0-a209-3cfb4d28fddd', '31b9a4e6-2c22-4de0-82fc-b1129744d2ac', '32c9992d-97c0-4399-b666-c685bd4f37d8', '32d04422-8a3a-43c1-805e-bae929094c05', '336b0f50-b601-4271-9c57-3e56db5a36be', '348b0f27-f1b4-437c-b653-6cb5be962350', '34e08286-0397-46ba-a88c-683ea9f6ae7a', '34f172be-156e-4bb7-932b-b595eac22ace', '35a14d24-7da5-44d2-8e02-f24633d1b398', '35b3369a-dea6-47a8-9dc4-23bd2ee054b5', '35daf71d-9599-4c6b-92a6-107d9f081a90', '37666232-1804-49c9-adcf-e77b06c2d7e0', '37c968ad-69d6-433f-83af-e3e16f0d8950', '37e6b14b-89dc-4252-b053-39723559e805', '385f18ca-7b95-4327-862f-5edba88206ad', '39077f06-0a40-4c98-b4c9-b3921196e4d9', '39fc90d7-dac3-4035-812f-8e1d56a474e1', '3a6429b2-2ab7-4f8d-8023-28bd6418fa12', '3bf227a4-ab5f-4c80-aba7-4e9d05cfcb15', '3cecf186-a770-4848-8109-21eae974e420', '3d211af8-9040-441e-9460-214c33eeb7a4', '3dce0c1e-de38-4879-b6c2-6dc7ff61da7f', '3ebf9ef0-36e8-425c-83d7-77b89d1ee3ae', '3ec66831-e892-427b-8a3e-b2abac1a0d9b', '4079d039-3d16-4796-9557-9e2bfbf99065', '408b1ccb-c52e-4f73-8244-0d7e4ee93147', '41146b0c-bc7f-4115-86f4-89a75d15cf70', '418774b9-f2ee-4597-af72-fec1e5aeceb3', '41a584e4-a4a4-4af2-9041-f99f975a89cf', '4322c2f7-cd66-4ea6-b3e8-cba58fa06671', '436827d5-dbce-4908-829c-8ec667daa27a', '44934271-e6d1-4fe7-8201-f00c20615723', '4576c2f2-0c11-4373-9d0b-119724bac0f3', '458f79bf-ee7d-4533-ab72-cc851136b73d', '46212b6d-25f2-4e86-b2e4-58e141610d61', '46ce452e-96ab-4d88-b183-a3fedcf778bc', '471c9207-e2c9-463a-aae2-350bb8d929ae', '474ab5ca-00a4-4f62-9726-ace3534fe86e', '475627d8-50f5-4b79-b386-3491ac368555', '4758d1f0-c093-4a16-abcb-53319167e859', '4844cb30-1cc7-47c5-9aac-dfde8c4927b2', '487c88e5-526d-4bab-ac86-c7e55f170627', '48a3dd0e-244f-4cf9-a04c-6a63a8c9948b', '4a2018ae-4d4b-4cad-bbf3-1ede1ee0d5cf', '4a4b7e86-48a5-4359-bcd2-741e65b4528f', '4a844214-e519-43d9-aac4-50dc23680cdf', '4b0dab95-2c2f-4c6f-9452-5d8bcde12adc', '4bec35fb-7db2-4e56-8396-b3009a061c37', '4c9c4da2-f637-4998-8a5f-11a617416aa9', '4d8afb24-359f-455a-9cfd-897265c00ab3', '4dc05b88-b027-4b7b-8713-674da1834670', '4e6f010f-1328-4f6b-ba63-37634f4ed13b', '4f566375-28e7-4f25-b120-c3e3bc91f2cf', '50d56fee-e7d7-4e07-aa2d-1f9ecf6672a4', '51b22c8f-a253-447f-97e8-975a1bbdb725', '51be10fb-ca75-41f4-8f9b-bcfdb4b5f02d', '52208e76-e105-4047-8f57-62ec252ee9fc', '525d739f-fcad-4688-aed7-aa13c891b862', '52753ddb-4afd-4d6c-b97f-849771620334', '52f8242f-1c70-4f09-817f-03a8c943c939', '530b7d54-9dea-461c-a7aa-f4d75e703dfc', '540e892f-50eb-4f2f-a574-9278998620c3', '55a2b303-89e6-4d5d-ba6c-c3d82ca660cf', '55dcca25-d135-443f-9720-f6eeac2adfea', '56573145-b6d9-4205-a968-98cac403c766', '568b8f34-de7f-40c0-b188-4c0fa2447f1f', '5728edff-57f2-426a-b9a9-7cff69154cd9', '5807f345-99fd-4db1-aec3-cef1772e4d9c', '586f1d6a-8aaf-494e-a69a-de4bb4c85908', '5883cce0-22ca-4e78-92dd-e51795026396', '592763b3-9dac-4b32-9a5b-83317ca5090c', '592971a0-afa6-4f9e-978f-2422450a9c41', '5a7c023c-59d0-426c-a3ae-fc7afac9b3a4', '5aa5274d-571b-46e6-8d7c-7376a4aca5f4', '5ab14ba4-243c-49dd-bcdf-caaed756a3e9', '5cac1743-624d-43f6-b9ec-6bb031e0415d', '5d474723-2e4f-4594-8e1b-139d6a6f5255', '5f0227b6-a9b0-4224-a12d-4925dfc962e8', '5f2aa965-1ccd-4f54-810f-232462d0051d', '5f42f40c-9421-4a8e-906e-a485ed9ecb65', '5f5ba973-3c2d-4032-bdc0-8bd49cd935e0', '5fe40f4e-5467-4e7d-8a1c-5caa94aa80aa', '603f0fd2-b671-4f23-a5f1-64a0c7db7544', '60807f9b-c491-49bb-ba32-ff770fa443f0', '62094897-64d7-4c51-96f9-867320c03a31', '62c4c08f-1996-40f3-b75f-09f7298f2bac', '62fe3ac9-cb70-4c93-8060-83b92b8b3da1', '6326912c-b86f-451d-a7f4-e76e128b3d6b', '659f71fa-82d7-4ade-b111-3e6091cbbc5b', '65a3d984-34f9-4f9a-b24c-fc89a2220c7c', '66343808-c6bb-4b5d-9471-fbf542b75a9f', '669c9dd7-f0fc-47d8-acb2-15dc133beb8e', '66a9cf1c-c75c-4c22-8b58-78e9dd211c75', '66d8886f-9318-4378-9015-36dbf08788d5', '66fb2fbc-6f63-49bc-923b-eca178d76a97', '6750ebaf-39cb-4d55-9cf8-9c2e832d6637', '67cfc8fa-3583-4f2b-a8c9-1c453c175f02', '67d1d9d1-7ce8-4e70-b4c6-f66aff7941ae', '6876a6ea-bc86-4b10-86a2-5583e9465173', '6928e44e-a4cd-49ed-9f84-491b41881b9d', '69a57505-6183-4b07-904f-b03dded05936', '6a5159e5-6e7f-4803-9ca6-97c1e016589a', '6a77c012-918c-4c1c-96b7-9b7fd5fd2370', '6c378b3f-5e9f-4642-8d65-961e630d09e7', '6e444608-bb24-4723-8725-b7fe827bd697', '6e6da499-1099-4fb0-a085-c825dce9e61a', '6ea56a95-eafc-4995-9858-bcbbc257da07', '6ea9f026-78f0-48f2-94b1-1d8cd21b8613', '6f88c5cb-72aa-4a38-bbbb-ad834c808fc8', '703d2ddb-e2fe-496d-86a9-6834500069e5', '70c434ab-f07b-40d9-a950-b2e73d513376', '70ec6d94-e11e-4c29-8a55-8cdf45b3dfe1', '713af8ac-24b9-43ae-9927-b9bac2330345', '719de2eb-b212-4055-8657-348cb70f17bd', '71e0b87a-09ec-45b8-8d06-ff726ddab3d5', '71ebbdaa-0252-443a-8e5a-666cf99c625d', '726d20fa-f6e4-4264-87dd-a5258d9bb06a', '7301aa8d-6de6-4c12-81db-af7f9528cbc9', '736bec1c-5747-4a5f-939d-c945d56a0e87', '741bba59-bb1a-4254-8989-59011f074307', '74af19dc-1b8f-4cc7-9238-d7c889a5efe2', '74ba8656-ba2d-4db0-9b92-f8eec178d3e3', '74d89839-7402-4c51-b4a8-3dbd49ca38ea', '762a8e33-a3df-401a-aaf8-dd68b88786b5', '771f1077-449d-4891-941b-66475726bdb7', '773f8565-6285-4a9b-9639-5442e27d14d6', '7813fd35-c330-467e-8f30-46b05af9990a', '789ae34b-28e0-4d2d-b432-78b1e1dbe942', '790c214c-fb25-4c24-bbe6-2ec8d8e92e45', '796f3860-4ab5-4e0b-ae20-4e592edfcf22', '7a675bc7-38da-46ed-9383-8238554e5791', '7a6bb34f-d719-47d4-9d3b-7dc78b3a47e1', '7a813103-488f-4d63-9eef-c082a1e9342d', '7b5e178c-5d36-4ec2-ae39-64ae1bf7a815', '7b635ffc-aa02-4d94-904c-213ef168a048', '7bb32fd3-e0d7-421f-8d49-c9d4c1e0d9d7', '7c79ac15-9996-4f43-b55f-9463b7121374', '7c8505cf-8fdd-4699-8671-add7df150195', '7ec86126-d184-4886-8af1-3d20cb2e0855', '7ed5bede-0845-4a47-b210-c44d625af9fb', '7edc37d3-c1e8-4866-b0d6-b4d528809b0b', '7edfb89e-a086-46b5-a42b-b477a715358c', '811b0224-da2b-4dd7-85cd-f4ea7aee4032', '811cdb65-0e69-4400-989b-9de93a83d1ae', '825df51f-dfc1-488e-a44f-fe3abb2c03ef', '82d9b8d4-4c87-4aa7-acab-e8401fb3947a', '8329831b-8e20-427b-9707-f39a188bb3ca', '834a36e0-b213-465d-a404-2451e9a5996b', '83bd6d97-43a0-4707-ab51-6e2a7bef51de', '8469d244-7b3e-429a-9f2c-210ba82b40d8', '84bdee0e-715e-4a2f-83c1-345657e26674', '8638a8ee-6909-417b-a46a-cca8cc114bf8', '872b4163-7141-4c38-8347-67e87f31975e', '8741e135-be24-4b87-9caf-fbe96ace1fec', '87dd1df0-e230-4d67-a4b1-0a47752e2b73', '8846b20d-d089-45a2-ba67-6da5bde91f59', '88d23bfb-c572-469b-acb6-4b67fd00474a', '8a4760ed-aecd-4dda-8aa8-99cda4de1b2f', '8a5a5d29-c213-4127-93a2-60d478074af6', '8c3f98f0-752d-4607-9bc6-8a22c154f161', '8c8dcb57-4e3d-4cb0-9c0a-0fc874113dcf', '8cc54650-4857-4e64-9df6-122251074a1c', '8d0d9958-abd1-45e7-b046-70331cd58d41', '8d50c653-6f29-4d16-b5a1-238f4eaa51a8', '8d520d69-01cd-49ff-87cc-94fb28bcd040', '8e6142f7-b73f-475a-93ee-55f3307358f4', '8efb3d88-4930-47c7-a311-57d133475374', '8fa1aff0-7e1c-4657-93ff-648dd32a798f', '8fb42aa4-b207-4e50-b52b-89e98f3f7120', '9003174e-9687-4686-afb2-975064fbc1ec', '9033cf31-e6f4-4c25-ac70-958dfddee253', '90454390-833f-4571-b4ec-b98f2ce57464', '904b2fac-f7b4-43ba-8548-196019bec175', '92b3fd35-78f3-4bd6-b267-47dccdbf9eca', '9353ad4e-5a1e-4500-88e6-35e4140a0cbd', '93576817-f644-4b57-84a7-4bd550d36620', '94675215-7bea-461d-b1d0-edcd0e050aef', '948be2f1-f630-43b2-902f-b439839b9291', '949ec4fc-8505-479b-8bd3-7ad09b59e9ca', '94fbacc6-73fa-41d3-a8bd-97178dacdde5', '95ed3e1d-fb43-447e-98cc-e21fb4bad99e', '97af7a58-2111-4cf8-9ba4-2c184908065f', '97df6725-41a3-4593-95a4-cfdb1619b30c', '97fa0166-97ca-42b1-be7e-214144ece840', '99602819-84d3-47fe-b7be-552719eb7ef5', '99a6e859-69a0-470c-8a36-4aa46980ca1b', '9a6928af-056b-402e-b331-f44092e784c8', '9a760cb3-01ed-4abd-b434-ed17b54f8702', '9b28dce4-11c1-46bd-b400-eae94ecede4d', '9b76d7a5-a3ba-47d3-bfa7-73ffbe6856ae', '9c265e4e-adc0-4ab3-aa3c-8ede7b9d00c4', '9c642785-3f3d-445b-ac18-eb1b7a643942', '9cd3846e-2cc8-4009-a44f-1c0af9c077d0', '9d0ad49d-918a-45f6-84b0-0cce0533cbcd', '9d5fc9a2-ba8a-451b-a1d2-efe9ce56ebc8', '9d62de11-d054-46d8-9e76-f2cebe50095d', '9e437d75-04ee-4c67-b06a-e5f15ffbb9da', '9ec71525-9330-447e-830e-115ce509170d', '9ef8f23d-eb82-4bc7-94d7-ba658d36c416', '9f1e6f04-e596-427e-ac0d-3eb83296b274', 'a09a51df-b544-485c-81ad-a99761ed8463', 'a0c9262b-1ad2-43ab-a11e-1bfc53c4ae9d', 'a0f0df5f-5d36-4569-8745-311cf1e32cf6', 'a0f89ece-c237-405f-8d5b-d6f9f59972b6', 'a14ce8b6-a4a5-44ae-9cde-a77e8641df76', 'a192b377-dfb9-4f45-967c-4517cb48483c', 'a1d81118-41ee-45b5-867f-ec678d74215a', 'a28dad93-cdf5-4b54-9a1c-f62bea039c33', 'a2e36150-045a-4020-96ef-a77702274c00', 'a3c65918-d018-47d1-8dab-5737a7368ab7', 'a43c5431-1604-4d96-a910-edde68f3ca2c', 'a470aecb-1e2c-444e-ad85-0ef76300b901', 'a53d0fd2-8e64-4bc5-b504-c2fc31db1789', 'a5eac5e6-5cbc-4ffd-a928-b2127b5d8ae8', 'a7176cfb-d3ad-4551-882c-2ca9aa78fd56', 'a7852ff8-3da3-46c3-9f05-6e00e554fcda', 'a7ce4ebe-a3c7-4e31-b8f4-e4a3b4b4edb6', 'a7f1298d-2687-4178-bae2-7ec7a07178d8', 'a8f400fb-2f40-4caa-873a-9ab8a9199a7b', 'a8f8cd95-ec02-4af4-adb1-0cf951d15fcd', 'a937e6c9-80bd-4779-a4f7-512918a01503', 'aa3c7564-668f-4020-936b-082e4c312a1c', 'aac25b6d-9249-437c-97e6-73924cfb7d2a', 'aaf66e91-ec04-4bd0-9664-d61ce5a8f55b', 'abb7dfed-0e96-4ea0-8dfe-1499ce967ff4', 'abefaa09-b706-43ae-a53e-5aa1f8d7022a', 'ac6b7ecf-f6be-421d-b7d4-1785480a7954', 'ac87edf7-22df-4d5a-92ce-f2a8f1ce1a84', 'ad1a5f0c-d586-408a-a233-764331ae7838', 'ad387588-d1e3-403e-91e0-e3b1be8e50d8', 'ad5f73a5-1ce3-4b1c-a914-1cb598321357', 'ada345fc-eae6-4d83-adfe-684a25bf0c54', 'adf83354-7e0a-49c1-8b76-4456b3d7850f', 'adfbcb74-2a63-488d-9a0f-ac7e0e6b634f', 'ae49e827-30bd-4519-a329-02b7c2b19c5d', 'aea4ca3f-5cfc-48f3-9098-58acde270d98', 'af477306-d5dc-4807-b505-28a2ff5614b9', 'aff55835-3c26-4b8c-a463-dfb08901cb18', 'b0995819-2468-4bd0-b1fa-86e43540f5c1', 'b0ad8280-3c9d-438d-9b03-2a9d95fd7366', 'b0f034ca-f165-4f61-ac30-e242ead48e40', 'b2163ef5-32d9-45a4-a91f-28f401dc7be4', 'b24a1599-a83e-4e78-85f8-8092e164f745', 'b2c884cf-00a7-48c7-ad69-2dd42bb3d12f', 'b362e2b8-bb77-4f3b-b166-6bb21f9a3982', 'b395b1ee-d947-4598-bfb7-631de597d376', 'b39e8d01-c900-425a-981e-aeeee8391fc8', 'b3a658cb-bc91-4763-bc50-385e7c2a04b5', 'b408e67d-92e3-4c47-923c-bd519277ceb2', 'b676d333-1d37-4621-8f6e-584b3069685d', 'b7395598-764c-437e-baa0-660be1b41c3c', 'b7a75800-6330-45b7-a89f-5a0b3b8d4e4b', 'b8394498-9bf3-4014-84c7-124ce1b0f731', 'b85b7a2d-df3c-4514-82e7-a091b3f8e932', 'b93915eb-6990-4feb-b5c4-45cf78dd94be', 'b94b2ee8-9155-4c26-b666-c04e757c22e8', 'b9cb3394-a39b-4282-9526-0b1d392d556f', 'ba44ef89-f542-4373-a742-86ff445a7e1a', 'bb39a8f1-2582-47f8-8958-06ca4ccf9565', 'bb3fca68-4c7e-4811-b3c0-0d6fce72e36a', 'bb95892b-8518-4370-a740-e34f7916ddad', 'bc4d5bc4-2f91-404e-8607-678bab7ea551', 'bca985c8-1932-4c2c-b362-94bd2186680f', 'bd086458-8a15-496f-85e7-c99a20d24570', 'bd23ad4d-16fb-40c6-9bbd-00be0cfdfc4f', 'bd763cc5-9a07-4844-a293-d7002e07c3c8', 'be03f0da-b157-4899-aa9c-1f4c431c8ce2', 'be31046a-a796-4d25-9881-64168ab682d7', 'bf4b7752-985a-4c43-a38f-1e043ea4ec8c', 'bfb6a2ba-bc52-4181-85dd-6c911f1144ae', 'bfd5468e-1165-419f-85ef-cca37845e01d', 'bfe1ab14-ae0d-4cb0-a926-83c85f34ce27', 'bfe5f313-49d7-48f0-838d-21420f3e8bf9', 'c016b813-1369-4691-bedf-e8731e5c2c45', 'c1015bef-85c4-4f09-a239-a190529c680a', 'c10466e9-81f7-44ec-b716-ac3c3dbb2f30', 'c1ad6ab5-0beb-445a-bb99-4322c697c5bb', 'c1c9bd0f-479a-4378-b04c-2bf8a629bb6d', 'c21245ef-ada0-4b15-9cff-0aefa8663ea6', 'c28069bd-97b8-407f-9396-911d09ba01a4', 'c34afb00-0bbe-4c17-9008-77bf3c0f31c5', 'c3cd7b54-8643-478f-87c1-d2e05adbbabe', 'c3d03633-74d9-4b3a-8128-8e9e969779e3', 'c3d80ff2-ab47-4f9c-9c03-f54c45b39652', 'c40a5e92-97d8-4497-9eaa-ac550173b2c5', 'c43be4e4-aaa9-47d9-8352-0eaad0d4c4d7', 'c4f3af21-6b11-41f9-bcfd-ea2bd227d041', 'c4fdc85e-9853-4302-9564-8fa19002b0b2', 'c5725cc6-481e-4c7a-baad-97c60ec3770e', 'c57c2ea2-74d5-47bb-970a-40b5bc04f4e7', 'c5912794-af3a-4d1b-934c-83387c08b320', 'c626c08a-48a9-49f9-9691-ab4efdac5e4c', 'c64704d8-ae37-43b9-b588-fcadd2b2969c', 'c6a0202e-9919-4613-8f3e-15dd94240aee', 'c6d701be-7f14-44c4-a1b5-53eb2f401ad9', 'c6fdc4cd-4037-4528-9989-965265d846d3', 'c760ca36-2566-40d5-8cc5-f6f5e060a654', 'c7e9ebe3-5a74-42dc-bf59-bbf02e057e32', 'c925424a-8c5c-4fd7-9696-01aed894270e', 'c92a979d-64e4-4bfc-a41a-4dc949e865e9', 'c94a259b-ee22-473b-ba33-e6c2b3b5aace', 'c9b7d0a2-ae5f-4140-8ebe-ca17a58bf8b4', 'c9cfec9b-4c9a-4e04-be3a-a616cf561820', 'ca3fffbb-83f3-419e-8647-23ac9985639b', 'cac3b4df-bd29-4757-b46b-6335d1b53b81', 'cb1f6838-6a2e-415b-8e87-aa7a4539df55', 'cb59dfb1-a948-42bf-83f6-48806d5657c5', 'cc8e3da0-7392-4414-9991-ece8e0f09ba0', 'cccf0adf-5da4-4054-b13f-60eabde522ca', 'cd65d836-f55b-43d1-b510-2782b869ad5e', 'cd99e875-cda2-4082-b9be-e81b52f8bbe2', 'ce0c0b1e-a6f8-4989-b1cf-4e52a9d918c0', 'ced2cc7b-54e9-49d0-801d-183664bf090b', 'cee8023b-3470-4883-bab8-ac58970f4c20', 'cf44a1cb-73c2-4103-b076-9c5515240557', 'd023fb3b-6be1-4825-89b9-8588baf48d8a', 'd1f7e51c-e412-4002-9f8a-66a6e585db5a', 'd2690411-da10-4573-91a0-deed92fbb932', 'd313352a-996e-4069-937d-5ac7b33239c2', 'd3344567-0f3f-4913-8299-5e16eae63a75', 'd3767f07-6741-453a-8cd9-0fd94b0db2e2', 'd39b1ddc-2253-4132-8e38-8eaeaa5a367e', 'd4cc7828-920f-44f4-944a-8c0e4d8358a4', 'd53846c9-bc94-425a-b576-5dbf8192482c', 'd586106d-0b52-4268-82cb-e9b2e9b7c1f7', 'd5917520-0988-4838-bb48-e166c5a993bd', 'd5fe42be-8ebe-4d44-80a4-c5eaefffe7d7', 'd60ff94c-82d9-4b90-a87b-dbf7e6feb975', 'd61275f7-46fe-407e-b6b1-b2ee7b13ba31', 'd8025311-2e2f-43c0-81c8-6ec174773469', 'd80f6136-22d5-4930-8e89-8ead1042e4ea', 'd843b2c1-3799-48f3-a721-a99bf8807cca', 'd87b4f93-2219-4fb5-8566-343b85be3be3', 'd890fef7-55a8-418e-a083-577982accd48', 'd8974ba5-0d7e-4164-9d40-13bddcb613d9', 'd8c04936-9921-46f7-bda2-075ead8b400c', 'd8e1ada1-40ec-410a-9a69-2d839beaf3b9', 'd949000b-4660-4cea-8c0d-50a98bf71d24', 'd96099bc-c88d-401b-a9ab-740bcfdb4e58', 'd9b1d1f5-99db-41b2-9efe-1bff6e0d5606', 'da77607f-3166-4dc8-8b82-bc301eae5354', 'da89021a-112a-416a-803a-eb6c7596779c', 'da9738c9-c840-4134-9aa2-208100ffb228', 'db1fba43-3c8e-49e7-a718-243660c3c9fd', 'db36fdb5-33df-4538-b337-d9358d600024', 'dbf50a7a-232b-4701-9b57-67d5bbd1c6dd', 'dc0c802e-cd3b-4d77-a354-8d99b3cab1b0', 'dc20e433-7b27-41ac-89ab-262d5eb4ecbf', 'dc2ac252-5195-48d9-9be9-c1ecc0eb8d3b', 'dcc1231d-8a61-4d62-a74e-ad6b7124d27c', 'dd097e06-fec1-4ff4-a7b3-09d74f48ef93', 'dd3c9123-8bef-4286-bd1f-eaf0a7ae79cd', 'ddadd226-46c4-4380-a93a-f00f15079940', 'de6ecb1d-5468-4beb-906d-d1454417ce9e', 'dea371cb-61ad-41f8-a4ff-539dbb4f75f6', 'dead4e5d-5c27-453a-878f-adbdd4ec0a7f', 'df44660a-6c17-41f8-9d18-6ef62612745c', 'df7ca260-77c1-49c3-9694-4c87e325489a', 'dffebdd0-7aac-4241-9580-a624e185691e', 'e12edcb6-36c4-4ee0-93c8-10a844dad98b', 'e1c8763e-c853-43d2-a523-a262f0616e92', 'e30b81a3-85e9-4e08-b057-294cfbd7d952', 'e348306d-ab6d-4941-b378-0183228408b4', 'e387580a-f235-407e-a172-160267239e40', 'e43226a9-e198-424c-81ef-aa0d7c0854d0', 'e4aa4f85-05af-4514-817f-ab992679a879', 'e4ccf7a9-5645-462a-b5cd-fdd6c8c80c0b', 'e5a5e7b1-f19e-4ad2-9f1d-bea2c6a8111f', 'e609ba76-d458-4aa5-87ce-51c5174c00dc', 'e6a7f1a3-42cd-4753-8108-78fad2f2df1c', 'e7b79fc0-1ae1-4a21-9949-457fe9d9ea9d', 'e80ca3e6-f14a-4a5b-b8e8-f5b862767679', 'e83ffafa-e424-4565-9e84-33e9880ccb46', 'e8e6f490-16f1-4f4d-b407-d73297316fe5', 'ea48106f-a06c-4095-bb99-d9eb7b28882c', 'eabdff27-6fcb-44f7-a571-b02f146db822', 'eaf646cb-f385-4164-a143-405f12fe8b49', 'ebb48a67-43fe-43a2-837f-de00d7e0d86d', 'ec3f388b-5671-4cf8-8d74-69377b103b84', 'eebea101-c967-48dc-89df-9af5328ff809', 'ef3e33c6-2767-428b-bb85-eabdc00c94eb', 'ef7b6b80-63b7-47da-8629-0642c252f660', 'f1711674-d7f2-485e-86d9-f8184acfa02d', 'f1da54c5-b0ef-4245-930e-d0b82b3bcbf3', 'f2545920-8eb0-4a7c-a1b8-8e4dfc29e6ec', 'f2932fe1-3896-4a94-b89e-1f2b452776b9', 'f2d1e7cc-93d5-4747-99aa-3a1ff4ae8f2c', 'f31435ad-3cc5-4d2c-a074-e7ed922d4069', 'f369eb08-ee50-4ac6-bfa2-3f12d9915703', 'f3c445bd-bb34-46a3-ac47-3f0daf24f7c2', 'f41aa32e-8efb-4c80-a38d-d14e65a07b98', 'f44fe739-4655-4381-9510-2d106f2ede78', 'f4adcf37-5b09-4366-8873-b9f47c641596', 'f4bdd3ee-b969-4221-b270-2ac9dd9cbd39', 'f4cb2ff0-098a-4ecc-9b1b-c3df6afa55e1', 'f512a054-dba2-41be-9bbf-53a28d649c4a', 'f6bee17c-1282-4a53-a56a-7b921b0c061c', 'f758a602-d9ef-479b-886b-d310c3b151e8', 'f79ac2cb-89c6-4b96-b58d-388eb3cb0e39', 'f7cff230-9c81-407e-a1c4-599575c8de4a', 'f8b6480d-4ef4-4eb6-9613-634503f10d43', 'f9479d08-9dec-43a1-98b2-e7cc31c7ff1a', 'f9ccdc46-4850-4eb9-b3e7-88c2c6822aa7', 'fa4f8c5f-3360-4f3e-bbd2-4fcec5883292', 'fa5d8754-25a4-48a8-bba9-ab14a53683fa', 'fb0edb23-9390-4421-830e-7fb38bfe2fca', 'fc116e29-ebc7-43b3-89fe-e92f8f2b3d98', 'fd252528-ffad-4a1d-87a3-0a097f812d67', 'fd466aee-18a9-4795-a64e-ebf79d7000f9', 'fd9bc160-3dcc-40bb-9809-e70e046bfded', 'fe208bfb-8bda-4282-93a3-695bd47afee9', 'fe913d31-8328-4f6d-bb0d-3fa996ba2652', 'ff886299-9ae7-4df6-a8c3-ea0fe6ee8306', 'ff8eb83b-c561-4e09-b52c-c4530ca57891'}
# --- Variables de entorno ---
directorio = r"G:\20261018_100m"
year = 2026
print("Indexando archivos... por favor espere.")
archivos_por_fecha = {}
patron_fecha = re.compile(rf"\b{year}\d{{4}}")

for raiz, directorios, archivos in os.walk(directorio):
    #directorios[:] = [d for d in directorios if d not in carpetas_invalidas]
    
    if str(year) in raiz:
        for archivo in archivos:
            if archivo.endswith(".tiff") and "qf" not in archivo:
                # Buscamos el patrón 2021XXXX en cualquier parte del nombre
                coincidencia = patron_fecha.search(archivo)
                
                if coincidencia:
                    fecha_encontrada = coincidencia.group(0) # Extrae el texto '20210218'
                    
                    if fecha_encontrada not in archivos_por_fecha:
                        archivos_por_fecha[fecha_encontrada] = []
                    
                    archivos_por_fecha[fecha_encontrada].append(os.path.join(raiz, archivo))


print(f"Indexación completada. Se encontraron {len(archivos_por_fecha)} fechas con datos.")


for month in [10]:
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    fechas_validas = []

    while first_day <= last_day:
        fechadn = first_day.strftime("%Y%m%d")
        final_lista = archivos_por_fecha.get(fechadn, [])

        if final_lista:
            try:
                # 1. FUSIONAR (Merge) - Equivalente a gdal:merge
                src_files_to_mosaic = [rasterio.open(f) for f in final_lista]
                mosaic, out_trans = merge(src_files_to_mosaic, nodata=0)
                out_meta = src_files_to_mosaic[0].meta.copy()
                
                # 2. CALCULAR ESTADÍSTICAS BÁSICAS (Verificar si no es nulo)
                # Simulamos: stats.maximumValue != 0
                max_val = np.max(mosaic)

                if max_val > 0:
                    output_tiff = f"G:\\cmpc\\agua100\\{first_day.strftime('%d%m%Y')}_swc4_26_100.tif"                    
                    #output_tiff = f"G:\\aguaPirque\\{first_day.strftime('%d%m%Y')}_swc44.tif"
                    # 3. GUARDAR EL RÁSTER (Equivalente a QgsRasterFileWriter)
                    out_meta.update({
                        "driver": "GTiff",
                        "height": mosaic.shape[1],
                        "width": mosaic.shape[2],
                        "transform": out_trans,
                        "compress": "lzw",
                        "count": 1,
                        "nodata": 0 # Equivalente a setNoDataValue
                    })
                    mosaic[mosaic == 65535] = 0 
                    with rasterio.open(output_tiff, "w", **out_meta) as dest:
                        dest.write(mosaic[0], 1)
                    
                    print(f"Exportación completada: {output_tiff}")
                    fechas_validas.append(first_day.strftime("%Y/%m/%d"))
                
                # Cerrar archivos abiertos
                for src in src_files_to_mosaic: src.close()

            except Exception as e:
                print(f"Error procesando {fechadn}: {e}")

        first_day += timedelta(days=1)
        

    # --- Generación de SQL (Igual que tu lógica original) ---
    if fechas_validas:
        sql_final = "INSERT INTO cmpc.disponible_fechas(fecha,tipo) values " + \
                   ",".join(f"('{f}','SWC4')" for f in fechas_validas) + ";"
        logger.info(sql_final)

        for fecha in fechas_validas:
            fecha_sep = fecha.split('/')
            f_org = fecha_sep[2] + fecha_sep[1] + fecha_sep[0]
            # Nota: Aquí asumo que mantienes tu lógica de SQL para PostGIS
            sql_base = f"""-- estadisticas upf
                INSERT INTO cmpc.estadistica_swc( gid_poligono, fecha, promedio, minimo, maximo,acumulado,desviacion)
                SELECT 
                    p.gid,
                    '{fecha}' as fecha,
                    AVG(p.val) AS promedio, 
                    MIN(p.val) AS minimo, 
                    MAX(p.val) AS maximo,
                    SUM(p.val) AS acumulado,
                    STDDEV(p.val) AS desviacion
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, p.the_geom,TRUE,TRUE))).*,p.gid
                    FROM "{f_org}_swc4_26" r
                    JOIN public.fundos_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0
                group by p.gid;
                --calculo estadisticas utb
                INSERT INTO cmpc.estadistica_swc_utb(
                    gid_poligono, fecha, valor)
                SELECT 
                    p.gid,
                    '{fecha}' as fecha,
                    (p.val) AS valor
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, ST_Buffer(p.the_geom,-0.01),TRUE,TRUE))).*,p.gid
                    FROM "{f_org}_swc4_26" r
                    JOIN public.ri_utbs_riego p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0 ;
            """
            logger.error(sql_base)

logging.shutdown()
