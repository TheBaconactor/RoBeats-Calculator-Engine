-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Time elapsed: 10 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = {
    ["DEFAULT_CREATE_PET_PARAMS"] = {},
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v3 = {}
        local v_u_4 = v_u_1:new()
        v3.cons = function(_) --[[ Name: cons ]] --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_4 ]]
            local function f_add_pet_data(p5, p6) --[[ Name: add_pet_data ]] --[[ Line: 14 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_4 ]]
                v_u_2:is_false(v_u_4:contains(p5))
                v_u_4:add(p5, (require(game.ReplicatedStorage.Pets.PetInfo:FindFirstChild(p6))))
            end;
            f_add_pet_data(1, "PetHelpfulAlien")
            f_add_pet_data(2, "PetValentinesLisa")
            f_add_pet_data(3, "PetSimilarOutskirts")
            f_add_pet_data(4, "PetWizardTowerHeroes")
            f_add_pet_data(5, "PetMiraiTowerHeroes")
            f_add_pet_data(6, "PetMisomyl")
            f_add_pet_data(7, "PetPonchi")
            f_add_pet_data(8, "PetCametek")
            f_add_pet_data(9, "PetWaterflame")
            f_add_pet_data(10, "PetBirthdayAlien")
            f_add_pet_data(11, "PetLeaF")
            f_add_pet_data(12, "PetGoldn")
            f_add_pet_data(13, "PetHyperPotions")
            f_add_pet_data(14, "PetARForest")
            f_add_pet_data(15, "PetBRZ")
            f_add_pet_data(16, "PetKurokotei")
            f_add_pet_data(17, "PetLaur")
            f_add_pet_data(18, "PetLandino")
            f_add_pet_data(19, "PetGarlagan")
            f_add_pet_data(20, "PetUndeadCorp")
            f_add_pet_data(21, "PetRiran")
            f_add_pet_data(22, "PetGeoxor")
            f_add_pet_data(23, "PetFreedomDive")
            f_add_pet_data(24, "PetFreedomDiveMetal")
            f_add_pet_data(25, "PetMaliboux")
            f_add_pet_data(26, "PetRingmasterRoxie")
            f_add_pet_data(27, "PetMonstercat")
            f_add_pet_data(28, "PetSlushii")
            f_add_pet_data(29, "PetWhippedCream")
            f_add_pet_data(30, "PetFNFBoy")
            f_add_pet_data(31, "PetFNFGirl")
            f_add_pet_data(32, "PetTeamGrimoire")
            f_add_pet_data(33, "PetF777")
            f_add_pet_data(34, "PetSeura")
            f_add_pet_data(35, "PetCreo")
            f_add_pet_data(36, "PetRutra")
            f_add_pet_data(37, "PetDarkCat")
            f_add_pet_data(38, "PetReku")
            f_add_pet_data(39, "PetAIBomb")
            f_add_pet_data(40, "PetArdolf")
            f_add_pet_data(41, "PetTobu")
            f_add_pet_data(42, "PetSeatrus")
            f_add_pet_data(43, "PetHalloweenTeresa")
            f_add_pet_data(44, "PetSlynk")
            f_add_pet_data(45, "PetTVRoom")
            f_add_pet_data(46, "PetSchoolMarie")
            f_add_pet_data(47, "PetKobaryo")
            f_add_pet_data(48, "PetCakeEventChef")
            f_add_pet_data(49, "PetWinterMarsha")
            f_add_pet_data(50, "PetSoundSpace")
            f_add_pet_data(51, "PetSilentroom")
            f_add_pet_data(52, "PetTPazolite")
            f_add_pet_data(53, "PetSpringMattie")
            f_add_pet_data(54, "Pet8BitAlien")
            f_add_pet_data(55, "PetHyun")
            f_add_pet_data(56, "PetKanro")
            f_add_pet_data(57, "PetChroma")
            f_add_pet_data(58, "PetSummerZara")
            f_add_pet_data(59, "PetSynthion")
            f_add_pet_data(60, "PetEmoCosine")
            f_add_pet_data(61, "PetBossfight")
            f_add_pet_data(62, "PetRaveDJ")
            f_add_pet_data(63, "PetAutumnLisa")
            f_add_pet_data(64, "PetVocaHiku")
            f_add_pet_data(65, "PetBunnyZara")
            f_add_pet_data(66, "PetJuggernaut")
            f_add_pet_data(67, "PetHalv")
            f_add_pet_data(68, "PetYou")
            f_add_pet_data(69, "PetSurvivorStarlet")
            f_add_pet_data(70, "PetSkylate")
            f_add_pet_data(71, "PetAaaa")
            f_add_pet_data(72, "PetKagetora")
            f_add_pet_data(73, "PetUSAO")
            f_add_pet_data(74, "PetNanobii")
            f_add_pet_data(75, "PetYooh")
            f_add_pet_data(76, "PetBlack17")
            f_add_pet_data(77, "PetUjico")
            f_add_pet_data(78, "PetRockStarlet")
            f_add_pet_data(79, "PetFusq")
            f_add_pet_data(80, "PetLappy")
            f_add_pet_data(81, "PetTranceZara")
            f_add_pet_data(82, "PetWaterflameElectroman")
            f_add_pet_data(83, "PetBlackY")
            f_add_pet_data(84, "PetKagi")
        end;
        v3.get_name_for_petid = function(_, p7) --[[ Name: get_name_for_petid ]] --[[ Line: 106 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            return v_u_4:contains(p7) ~= true and "?" or v_u_4:get(p7):get_name();
        end;
        v3.get_data_for_petid = function(_, p8) --[[ Name: get_data_for_petid ]] --[[ Line: 112 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            return v_u_4:get(p8);
        end;
        v3.contains_petid = function(_, p9) --[[ Name: contains_petid ]] --[[ Line: 113 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            return v_u_4:contains(p9);
        end;
        v3.get_pet_id_list = function(_) --[[ Name: get_pet_id_list ]] --[[ Line: 114 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            return v_u_4:key_list();
        end;
        v3.count = function(_) --[[ Name: count ]] --[[ Line: 115 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            return v_u_4:count();
        end;
        v3.get_pet_info = function(_) --[[ Name: get_pet_info ]] --[[ Line: 117 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            local v10 = {}
            for v11, v12 in v_u_4:key_itr() do
                v10[#v10 + 1] = {
                    ["pet_id"] = v11,
                    ["name"] = v12:get_name(),
                    ["materialid"] = v12:get_material_id(),
                    ["rarity"] = v12:get_rarity()
                }
            end;
            return v10;
        end;
        v3:cons()
        return v3;
    end
}
local v_u_14 = nil
v_u_13.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 135 ]]
    --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_13 ]]
    if v_u_14 == nil then
        v_u_14 = v_u_13:new()
    end;
    return v_u_14;
end;
return v_u_13;
