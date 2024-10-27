import subprocess
import os
import json
import utils.json_utils as json_utils

class VersionParser:
    def __init__(self, output_dir, depot_downloader_dir, steam_username, steam_password, verbose=True):
        self.app_id = '1422450' #deadlock's app_id
        self.depot_id = '1422456' #the big depot

        self.output_dir = output_dir
        self.depot_downloader_dir = depot_downloader_dir
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.verbose = verbose # future proofing for verbose argument
        self.depot_downloader_output = os.path.join(self.output_dir, 'DepotDownloader')
        self.versions = {}
        self.versions_path = os.path.join(self.output_dir, 'json', 'versions.json')

    def _load(self):
        # Load versions to memory from versions.json
        versions_path = self.versions_path
        if os.path.exists(versions_path):
            with open(versions_path, 'r') as file:
                self.versions = json.load(file)
        else:
            raise Exception(f'Fatal error: {versions_path} not found')
            

        if self.verbose:
            print(f'Loaded {len(self.versions)} versions from {versions_path}')

    def _get_missing_versions(self):
        # Find empty manifestid's in the versions.json
        missing_versions = [manifest_id for manifest_id in self.versions if not self.versions[manifest_id]]

        num_missing_versions = len(missing_versions)

        if self.verbose:
            print(f'Found {num_missing_versions} missing versions to parse')

        if num_missing_versions == 0:
            return {}
        
        return missing_versions

    def _parse(self, versions):
        parsed_versions = {}
        num_versions = len(versions)
        curr_num_versions = 0

        try:
            for manifest_id in versions:
                # Run the depot_downloader command
                subprocess_params = [
                    os.path.join(self.depot_downloader_dir,'./DepotDownloader'),
                    '-app', self.app_id,
                    '-depot', self.depot_id,
                    '-manifest', manifest_id,
                    '-username', self.steam_username,
                    '-password', self.steam_password,
                    '-remember-password',
                    '-filelist', 'input-data/steam_inf_path.txt',
                    '-dir', self.depot_downloader_output
                ]

                result = subprocess.run(subprocess_params, check=True, stdout=subprocess.PIPE, universal_newlines=True)
                steam_inf_path = os.path.join(self.depot_downloader_output, 'game', 'citadel', 'steam.inf')
                if not os.path.exists(steam_inf_path):
                    raise Exception(f'Fatal error: {steam_inf_path} not found')
                
                # Open steam inf
                with open(steam_inf_path, 'r') as file:
                    steam_inf = file.read()
                
                parsed_versions[manifest_id] = {}

                # Parse each line
                for line in steam_inf.split('\n'):
                    split_line = line.split('=')
                    if len(split_line) != 2:
                        continue
                    key = split_line[0]
                    value = split_line[1]
                    parsed_versions[manifest_id][key] = value

                curr_num_versions += 1

                if self.verbose:
                    print(f'({curr_num_versions}/{num_versions}): Parsed {manifest_id} which contained VersionDate {parsed_versions[manifest_id]["VersionDate"]}')

            if self.verbose:
                print(f'Parsed {len(parsed_versions)} new versions')
        
        except Exception as e:
            # If any exception occurs in DepotDownloader,
            # first save what's currently parsed
            self._update(parsed_versions)
            self._save()
            raise e

        return parsed_versions
    
    def _update(self, new_versions):
        # Merge the parsed versions with the existing versions
        self.versions.update(new_versions)

    def _save(self):
        # Save the versions to versions.json
        json_utils.write(self.versions_path, self.versions)

        if self.verbose:
            print(f'Saved {len(self.versions)} versions to {self.versions_path}')

    def run(self):
        # new_versions = ['4092492988322622322','6281733434408860619','5081198370471146937','5868769883342719149','1110195483988403873','7250810548147076460','6711189121801377543','6975314021666512244','1134822727116852128','597535660973513789','5988645898034166679','6902773072939676130','4369698927496704222','5090297567061318298','1220112967339589835','4445709161970632714','869927414378704685','7409233371048534330','612899015237309789','7506840751260630350','4241662552020026285','2446401214387624837','2911875555140534363','7423908266886961121','9028183213409370282','7534726504634156525','7272722650114169681','8044786667015109853','5304276363691742940','4083897401960189175','5199345874697544332','8055730768379060909','8301626319375826882','6222273943798725796','6343036909963708404','2344015351211296016','6059123974617270196','2101187347995620337','8205479306390334189','4493145076681965169','6678948280131827378','2922445413059759371','3208927723092358040','3802566217947344592','8457411954997566876','5777549278038982684','2727450184447048827','3896233513427826638','4597997252167885997','7540491025264017760','559689273188132494','6569880859539964512','6953839252581323047','6377092319738139164','1796753196217801764','3888703579286624493','4177804092237165261','7739747708934865940','2502515025972263253','7228782279719241903','5604721781527506154','3940775172077954075','1558264121146302396','2669874087483310998','7077759894216867799','3159422876373397103','4338388029934374344','4669592844518320676','4448944656864615551','3921492920368224553','8590542750271090269','7818537816712071636','6754828840051311402','1205388541731512720','8494661584461021274','1743757208636711258','8986896931405252599','8584134807053004992','443323355425722313','3569122401113766710','2797258100636598929','6023595993027382382','8828387698301188','1982344895897433968','7601212445901204175','3362363365023623347','7389519204074484302','9117824023207771698','3931949366150044443','571428258974008041','212723827960620437','7531966821480206617','409502192204933244','6580131610705564023','6841443037131554230','3341810551027496497','4888465758757129411','2853676758991197186','2350766867727453047','58357994342504134','4745569323660308943','5547986301570402563','1682317656415564998','8419900641679331698','5516777253862139628','5888925540418915824','7510267314893368986','7568379704400122064','35226395596188333','2566941267379712021','4265222067702422526','1249795951701720724','2036639395491743121','3171481965223521138','5586205941927510163','629665074320775173','8054428535823173454','329343896823211186','7060417893867179414','6566634437861796152','6280897906387112301','3257603223321475634','9033814203781938158','5039595391771894419','7033698435015792100','5559171354573942559','8498395011617560577','7358150729940591778','4569320816740649284','2791460478218364625','6824367596786433824','4057390968941286811','2978560671395893873','5440643463150587731','3646032621482237743','7335128240951719409','2465759802143720877','355714314148622380','848189372795374541','7132013934227648985','2503040320853376063','1626343787016578765','6976498734576286866','6232874204020544416','6114907171353913122','688506849131143397','8871066833415302740','2009182789299622905','3327564633680637033','8556181921557365147','3459388303402873095','5622104336372118232','5245739343957219741','3523004364007244637','2052064259501390934','4137705485935858256','7910033866129119527','2144298780136741294','2492312602038566071','7901642034762472755','1783336646178848912','18176537398720907','5428963548222537564','7623656888252536408','6171106960179924593','8734515186746287949','4570598913357448058','5432977748551830754','8930938856536187310','6023452603275673367','3039831827764412364','5848504019386494554','1723765318771478890','2216076986805513220','6448082724923630265','2057943021973466326','4903307067940577389','8231438805893213329','3169970500223777116','8210715068951925851','4195839954238464999','6508525953428869902','1684699571004073228','860176996849311683','2641229586655379885','300375163423317425','1269724601750084580','2046847983034260803','244105533521085571','9036377012704104707','8047459740616699442','5966205424481512446','6571691746146766307','346698530959168080','3140541591402645288','3581043202836029056','5301376264804110866','7737964729577686475','6559042570630469002','6549737705588469431','5808668253231192597','4484595901620663127','3110187633805318512','1861001890761171851','3132969835880497759','8703339561161430209','3760387073600104317','5194317316011129362','5078108462705006950','4685071790261460845','2921001357498727543','1853346300215824569','8448464511807654390','5689926706968138646','4516873448495433061','6628326717927597214','5434640626784203959','3782667496249476864','34753734284690442','1360588026054422482','9146235054202519970','2263529655790080827','4965395473895127840','7321384253049881281','3561865154310484925','2710826836552972142','2570794383951212295','8429501682853024869','8879946331772584619','7606000191812053795','5918300309188559620','2352152186082413578','6428351590254383271','9063028592095036014','3481767060493275971','5728074628595895011','8180416771539151927','6992080732861608648','4766861011328513619','6415378154876530280','7364414571783454925','2358484780389270087','2905295356069525101','8768648122667582980','2978251239325221502','564660224624634715','4863524443402651046','6626715747285119482','6248677449187994389','5421681431482813671','3238647076813027524','149447951717576336','5527565481736354266','1106683171872905575','4826787032005773961','6140368531218914349','5047774726552675709','7901241237874125851','1906391260813464712','4206015977490630144','1544869847258220803','7733745725572607974','3292649524937987754','1008470491743606852','8617744918090422869','559023273746221547','2827711690054882176','336352009366265693','6919802919515413322','4346729122389334003','8841087779417111847','4087806510608892862','4816311520335667355','2758474894834139136','2902071174811834125','4994001100179481594','269534338158245743','7714250825719294028','3847089629117518426','8707448584436760722','6499695335046391959','3488331499852145297','6290048895690837076','3645726324020465476','6961654273888667223','8544258027710114004','8016912473945316532','5292640495668196476','1479529744471755773','4713363019838511031','5400681758695251799','4620757341576248645','9209032609355480385','8594144051665276499','4763491395482370270','1716316325510830448','1750585834208449162','1724612459237500665','2129209759404092266','7714492096121174150','5945074763507685012','6351544209451463370','283909953487078987','5476002124245442003','331188092586370516','6916376249836890015','1543909996994984116','1518818623564402592','7196258384474402679','5314781709396391508','3408223790767864147','9156334374682690927','3272729079208143443','4694064797845096958','2311553633334201202','2486086944767277626','3354052047795889088','8678331010899152100','3676225897182880774','3707274507581637435','1873035231375793235','5767808592076278922','7851698594411420366','3004026875235152312','3329028370390830445','694166570687875754','1462868816924048773','7575480259951816011','8472638347071333123','5411515690642447461','4388826931705517427','163997768485160973','8140581593892321536','4934762055049224811','7932062070839332272','2927431006612283207']
        # my_dict = {item: {} for item in new_versions}
        # json_utils.write(self.output_dir+'/versions.json', my_dict)
        
        self._load()

        missing_versions = self._get_missing_versions()
        if len(missing_versions)>0:
            parsed_versions = self._parse(missing_versions)

            self._update(parsed_versions)

            self._save()



        