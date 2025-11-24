-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Time elapsed: 14 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_5 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_shared(function() --[[ Line: 8 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    v_u_5 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
end)
local v6 = {}
local l_Equipment_0 = game.ReplicatedStorage.Equipment
v6.new = function(_) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): l_Equipment_0, (copy 3): v_u_3, (copy 4): v_u_2, (ref 5): v_u_5, (copy 6): v_u_4 ]]
    local v7 = {}
    local v_u_8 = v_u_1:new()
    local function f_add_to_equipment_dict(p9, p10) --[[ Name: add_to_equipment_dict ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_8, (ref 2): l_Equipment_0, (ref 3): v_u_3, (ref 4): v_u_2 ]]
        if v_u_8:contains(p9) then
            error(string.format("SPAvatarEquipmentDatabase:add_to_equipment_dict already contains(%d)", p9))
        end;
        local v11 = require(l_Equipment_0:FindFirstChild(p10))
        v_u_3:is_enum_member(v11:get_avatar_slot(), v_u_2)
        v_u_3:is_table(v11:get_gear_statmodifierobj())
        v_u_8:add(p9, v11)
    end;
    v7.cons = function(_) --[[ Name: cons ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): f_add_to_equipment_dict ]]
        f_add_to_equipment_dict(1, "TestShirt1")
        f_add_to_equipment_dict(2, "TestPants1")
        f_add_to_equipment_dict(3, "TestBack1")
        f_add_to_equipment_dict(4, "TestNeck1")
        f_add_to_equipment_dict(5, "TestHat1")
        f_add_to_equipment_dict(6, "TestFace1")
        f_add_to_equipment_dict(7, "GoonieDiscoGlasses1")
        f_add_to_equipment_dict(8, "GoonieDiscoHat1")
        f_add_to_equipment_dict(9, "GoonieDiscoPants1")
        f_add_to_equipment_dict(10, "GoonieDiscoShirt1")
        f_add_to_equipment_dict(11, "GoonieDiscoNecklace1")
        f_add_to_equipment_dict(12, "RandomHipBeanie1")
        f_add_to_equipment_dict(13, "RandomHipGlasses1")
        f_add_to_equipment_dict(14, "RandomHipHeadphones1")
        f_add_to_equipment_dict(15, "RandomHipHoodie1")
        f_add_to_equipment_dict(16, "RandomHipSweats1")
        f_add_to_equipment_dict(17, "XsitsuRetroAviators1")
        f_add_to_equipment_dict(18, "XsitsuRetroBoater1")
        f_add_to_equipment_dict(19, "XsitsuRetroBowtie1")
        f_add_to_equipment_dict(20, "XsitsuRetroSlacks1")
        f_add_to_equipment_dict(21, "XsitsuRetroSuit1")
        f_add_to_equipment_dict(22, "KonekoCatCharm1")
        f_add_to_equipment_dict(23, "KonekoCatHood1")
        f_add_to_equipment_dict(24, "KonekoCatShirt1")
        f_add_to_equipment_dict(25, "KonekoCatShorts1")
        f_add_to_equipment_dict(26, "KonekoCatTail1")
        f_add_to_equipment_dict(27, "XanaStreetCap1")
        f_add_to_equipment_dict(28, "XanaStreetChains1")
        f_add_to_equipment_dict(29, "XanaStreetJacket1")
        f_add_to_equipment_dict(30, "XanaStreetPants1")
        f_add_to_equipment_dict(31, "XanaStreetShades1")
        f_add_to_equipment_dict(32, "GamerExpensiveSuit1")
        f_add_to_equipment_dict(33, "GamerExpensiveBowtie1")
        f_add_to_equipment_dict(34, "GamerExpensiveFedora1")
        f_add_to_equipment_dict(35, "GamerExpensiveShades1")
        f_add_to_equipment_dict(36, "GamerExpensiveSlacks1")
        f_add_to_equipment_dict(37, "KaganCowboyGoggles1")
        f_add_to_equipment_dict(38, "KaganCowboyHat1")
        f_add_to_equipment_dict(39, "KaganCowboyPants1")
        f_add_to_equipment_dict(40, "KaganCowboyScarf1")
        f_add_to_equipment_dict(41, "KaganCowboyVest1")
        f_add_to_equipment_dict(42, "MightyProVisor")
        f_add_to_equipment_dict(43, "CasualGuitar")
        f_add_to_equipment_dict(44, "RebelLegendaryHat1")
        f_add_to_equipment_dict(45, "RebelLegendaryMask1")
        f_add_to_equipment_dict(46, "RebelLegendaryScarf1")
        f_add_to_equipment_dict(47, "RebelLegendarySash1")
        f_add_to_equipment_dict(48, "RebelLegendaryCoat1")
        f_add_to_equipment_dict(49, "RebelLegendaryTrousers1")
        f_add_to_equipment_dict(50, "MusketeerLegendaryHat1")
        f_add_to_equipment_dict(51, "MusketeerLegendaryMask1")
        f_add_to_equipment_dict(52, "MusketeerLegendaryRuffles1")
        f_add_to_equipment_dict(53, "MusketeerLegendaryEpaulette1")
        f_add_to_equipment_dict(54, "MusketeerLegendaryCoat1")
        f_add_to_equipment_dict(55, "MusketeerLegendaryTrousers1")
        f_add_to_equipment_dict(56, "MarshallLegendaryHat1")
        f_add_to_equipment_dict(57, "MarshallLegendaryMask1")
        f_add_to_equipment_dict(58, "MarshallLegendaryChains1")
        f_add_to_equipment_dict(59, "MarshallLegendaryShoulderpads1")
        f_add_to_equipment_dict(60, "MarshallLegendaryCoat1")
        f_add_to_equipment_dict(61, "MarshallLegendaryTrousers1")
        f_add_to_equipment_dict(62, "OniiOtakuBeanie1")
        f_add_to_equipment_dict(63, "OniiOtakuSpecs1")
        f_add_to_equipment_dict(64, "OniiOtakuMask1")
        f_add_to_equipment_dict(65, "OniiOtakuSweater1")
        f_add_to_equipment_dict(66, "OniiOtakuKhakis1")
        f_add_to_equipment_dict(67, "OniiHeartBlade1")
        f_add_to_equipment_dict(68, "HardcoreGuitar1")
        f_add_to_equipment_dict(69, "MetalGuitar1")
        f_add_to_equipment_dict(70, "AxeGuitar1")
        f_add_to_equipment_dict(71, "BlueColorBack1")
        f_add_to_equipment_dict(72, "BlueColorFace1")
        f_add_to_equipment_dict(73, "BlueColorHat1")
        f_add_to_equipment_dict(74, "BlueColorNeck1")
        f_add_to_equipment_dict(75, "BlueColorPants1")
        f_add_to_equipment_dict(76, "BlueColorShirt1")
        f_add_to_equipment_dict(77, "BlueColorBack2")
        f_add_to_equipment_dict(78, "BlueColorFace2")
        f_add_to_equipment_dict(79, "BlueColorHat2")
        f_add_to_equipment_dict(80, "BlueColorNeck2")
        f_add_to_equipment_dict(81, "BlueColorPants2")
        f_add_to_equipment_dict(82, "BlueColorShirt2")
        f_add_to_equipment_dict(83, "GreenColorBack1")
        f_add_to_equipment_dict(84, "GreenColorFace1")
        f_add_to_equipment_dict(85, "GreenColorHat1")
        f_add_to_equipment_dict(86, "GreenColorNeck1")
        f_add_to_equipment_dict(87, "GreenColorPants1")
        f_add_to_equipment_dict(88, "GreenColorShirt1")
        f_add_to_equipment_dict(89, "GreenColorBack2")
        f_add_to_equipment_dict(90, "GreenColorFace2")
        f_add_to_equipment_dict(91, "GreenColorHat2")
        f_add_to_equipment_dict(92, "GreenColorNeck2")
        f_add_to_equipment_dict(93, "GreenColorPants2")
        f_add_to_equipment_dict(94, "GreenColorShirt2")
        f_add_to_equipment_dict(95, "OrangeColorBack1")
        f_add_to_equipment_dict(96, "OrangeColorFace1")
        f_add_to_equipment_dict(97, "OrangeColorHat1")
        f_add_to_equipment_dict(98, "OrangeColorNeck1")
        f_add_to_equipment_dict(99, "OrangeColorPants1")
        f_add_to_equipment_dict(100, "OrangeColorShirt1")
        f_add_to_equipment_dict(101, "OrangeColorBack2")
        f_add_to_equipment_dict(102, "OrangeColorFace2")
        f_add_to_equipment_dict(103, "OrangeColorHat2")
        f_add_to_equipment_dict(104, "OrangeColorNeck2")
        f_add_to_equipment_dict(105, "OrangeColorPants2")
        f_add_to_equipment_dict(106, "OrangeColorShirt2")
        f_add_to_equipment_dict(107, "PurpleColorBack1")
        f_add_to_equipment_dict(108, "PurpleColorFace1")
        f_add_to_equipment_dict(109, "PurpleColorHat1")
        f_add_to_equipment_dict(110, "PurpleColorNeck1")
        f_add_to_equipment_dict(111, "PurpleColorPants1")
        f_add_to_equipment_dict(112, "PurpleColorShirt1")
        f_add_to_equipment_dict(113, "PurpleColorBack2")
        f_add_to_equipment_dict(114, "PurpleColorFace2")
        f_add_to_equipment_dict(115, "PurpleColorHat2")
        f_add_to_equipment_dict(116, "PurpleColorNeck2")
        f_add_to_equipment_dict(117, "PurpleColorPants2")
        f_add_to_equipment_dict(118, "PurpleColorShirt2")
        f_add_to_equipment_dict(119, "RedColorBack1")
        f_add_to_equipment_dict(120, "RedColorFace1")
        f_add_to_equipment_dict(121, "RedColorHat1")
        f_add_to_equipment_dict(122, "RedColorNeck1")
        f_add_to_equipment_dict(123, "RedColorPants1")
        f_add_to_equipment_dict(124, "RedColorShirt1")
        f_add_to_equipment_dict(125, "RedColorBack2")
        f_add_to_equipment_dict(126, "RedColorFace2")
        f_add_to_equipment_dict(127, "RedColorHat2")
        f_add_to_equipment_dict(128, "RedColorNeck2")
        f_add_to_equipment_dict(129, "RedColorPants2")
        f_add_to_equipment_dict(130, "RedColorShirt2")
        f_add_to_equipment_dict(131, "BoomBoxBlue")
        f_add_to_equipment_dict(132, "BoomBoxGreen")
        f_add_to_equipment_dict(133, "BoomBoxOrange")
        f_add_to_equipment_dict(134, "BoomBoxPurple")
        f_add_to_equipment_dict(135, "BoomBoxRed")
        f_add_to_equipment_dict(136, "KairohPurpleGuitar")
        f_add_to_equipment_dict(137, "RutraHoodie")
        f_add_to_equipment_dict(138, "PoppyHair")
        f_add_to_equipment_dict(139, "PoppyDress")
        f_add_to_equipment_dict(140, "PoppyShirt")
        f_add_to_equipment_dict(141, "CreoHoodie")
        f_add_to_equipment_dict(142, "HalloweenWitchHat")
        f_add_to_equipment_dict(143, "KuranteHeadphones")
        f_add_to_equipment_dict(144, "KuranteShirt")
        f_add_to_equipment_dict(145, "KuranteSkirt")
        f_add_to_equipment_dict(146, "KuranteWings")
        f_add_to_equipment_dict(147, "LandinoTriforceChain")
        f_add_to_equipment_dict(148, "LandinoFro")
        f_add_to_equipment_dict(149, "LandinoTrackPants")
        f_add_to_equipment_dict(150, "LandinoTracksuit")
        f_add_to_equipment_dict(151, "JustDanceWolfHead")
        f_add_to_equipment_dict(152, "JustDanceGuyMask")
        f_add_to_equipment_dict(153, "JustDanceGirlHair")
        f_add_to_equipment_dict(154, "JustDanceGuyShirt")
        f_add_to_equipment_dict(155, "JustDanceGirlShirt")
        f_add_to_equipment_dict(156, "JustDanceGuyPants")
        f_add_to_equipment_dict(157, "JustDanceGirlDress")
        f_add_to_equipment_dict(158, "SantaHat")
        f_add_to_equipment_dict(159, "ReindeerNose")
        f_add_to_equipment_dict(160, "TobuSweetShades")
        f_add_to_equipment_dict(161, "GarcelloHat")
        f_add_to_equipment_dict(162, "KepoBeanie")
        f_add_to_equipment_dict(163, "SlynkHat")
        f_add_to_equipment_dict(164, "SlynkShirt")
        f_add_to_equipment_dict(165, "SlynkPants")
        f_add_to_equipment_dict(166, "LisaBeret")
        f_add_to_equipment_dict(167, "GoldnHair")
        f_add_to_equipment_dict(168, "LaurHair")
        f_add_to_equipment_dict(169, "RiranHeadphones")
        f_add_to_equipment_dict(170, "CaptainHat")
        f_add_to_equipment_dict(171, "GeoxorWings")
        f_add_to_equipment_dict(172, "GeoxorHair")
        f_add_to_equipment_dict(173, "MaxzyMask")
        f_add_to_equipment_dict(174, "RingmasterRoxieHair")
        f_add_to_equipment_dict(175, "RingmasterRoxieGlasses")
        f_add_to_equipment_dict(176, "RingmasterRoxieTop")
        f_add_to_equipment_dict(177, "RingmasterRoxieSkirt")
        f_add_to_equipment_dict(178, "SoccerMommyGuitar")
        f_add_to_equipment_dict(179, "FNFBoyCap")
        f_add_to_equipment_dict(180, "FNFGirlHair")
        f_add_to_equipment_dict(181, "RestrictionEyepatch")
        f_add_to_equipment_dict(182, "RestrictionHair")
        f_add_to_equipment_dict(183, "RekuHair")
        f_add_to_equipment_dict(184, "UshiHair")
        f_add_to_equipment_dict(185, "ArdolfMask")
        f_add_to_equipment_dict(186, "ArdolfChest")
        f_add_to_equipment_dict(187, "ArdolfTail")
        f_add_to_equipment_dict(188, "HalloweenWitchCloak")
        f_add_to_equipment_dict(189, "HalloweenWitchSkirt")
        f_add_to_equipment_dict(190, "TVRoomBrain")
        f_add_to_equipment_dict(191, "SchoolSailorScarf")
        f_add_to_equipment_dict(192, "KobaryoHair")
        f_add_to_equipment_dict(193, "KobaryoGlasses")
        f_add_to_equipment_dict(194, "KobaryoShirt")
        f_add_to_equipment_dict(195, "KobaryoPants")
        f_add_to_equipment_dict(196, "SimilarOutskirtsBeanie")
        f_add_to_equipment_dict(197, "SimilarOutskirtsZipper")
        f_add_to_equipment_dict(198, "WinterMarshaHood")
        f_add_to_equipment_dict(199, "WinterMarshaCape")
        f_add_to_equipment_dict(200, "NewYearsBowtie")
        f_add_to_equipment_dict(201, "SoundSpaceEars")
        f_add_to_equipment_dict(202, "SilentroomPlanetBack")
        f_add_to_equipment_dict(203, "CametekFedora")
        f_add_to_equipment_dict(204, "ValentinesBear")
        f_add_to_equipment_dict(205, "TPazoliteHeadphones")
        f_add_to_equipment_dict(206, "LeafEye")
        f_add_to_equipment_dict(207, "BirthdayHat")
        f_add_to_equipment_dict(208, "ARForestHat")
        f_add_to_equipment_dict(209, "ARForestMask")
        f_add_to_equipment_dict(210, "HyunMask")
        f_add_to_equipment_dict(211, "KanroHeadphones")
        f_add_to_equipment_dict(212, "KanroChoker")
        f_add_to_equipment_dict(213, "ChromaHat")
        f_add_to_equipment_dict(214, "KurokoteiHair")
        f_add_to_equipment_dict(215, "KurokoteiNeck")
        f_add_to_equipment_dict(216, "FlamingoFloatHat")
        f_add_to_equipment_dict(217, "GarlaganMask")
        f_add_to_equipment_dict(218, "UndeadCorpHair")
        f_add_to_equipment_dict(219, "EmoCosineHair")
        f_add_to_equipment_dict(220, "BossfightMask")
        f_add_to_equipment_dict(221, "RaveHat")
        f_add_to_equipment_dict(222, "AutumnLisaHair")
        f_add_to_equipment_dict(223, "VocaHikuTie")
        f_add_to_equipment_dict(224, "NoScopeLoadout")
        f_add_to_equipment_dict(225, "JuggernautCannon")
        f_add_to_equipment_dict(226, "HalvPenguin")
        f_add_to_equipment_dict(227, "YouHair")
        f_add_to_equipment_dict(228, "SurvivorStarletHair")
        f_add_to_equipment_dict(229, "SurvivorStarletBack")
        f_add_to_equipment_dict(230, "SkylateMask")
        f_add_to_equipment_dict(231, "SkylateHoodie")
        f_add_to_equipment_dict(232, "JuggernautHair")
        f_add_to_equipment_dict(233, "AaaaMask")
        f_add_to_equipment_dict(234, "KagetoraNeck")
        f_add_to_equipment_dict(235, "TheGamesCrystal")
        f_add_to_equipment_dict(236, "TheGamesCape")
        f_add_to_equipment_dict(237, "USAOHat")
        f_add_to_equipment_dict(238, "NanobiiWand")
        f_add_to_equipment_dict(239, "AutumnFlowerHat")
        f_add_to_equipment_dict(240, "HalvHair")
        f_add_to_equipment_dict(241, "Black17Shirt")
        f_add_to_equipment_dict(242, "Black17Glasses")
        f_add_to_equipment_dict(243, "YoohPants")
        f_add_to_equipment_dict(244, "YoohShirt")
        f_add_to_equipment_dict(245, "UjicoBack")
        f_add_to_equipment_dict(246, "HeavyMetalHat")
        f_add_to_equipment_dict(247, "HeavyMetalJacket")
        f_add_to_equipment_dict(248, "FusqHat")
        f_add_to_equipment_dict(249, "LappyHair")
        f_add_to_equipment_dict(250, "TranceWings")
        f_add_to_equipment_dict(251, "USAOShirt")
        f_add_to_equipment_dict(252, "ElectromanHelmet")
        f_add_to_equipment_dict(253, "ElectromanScarf")
        f_add_to_equipment_dict(254, "BlackYHair")
        f_add_to_equipment_dict(255, "KagiHat")
    end;
    v7.get_equipment_for_id = function(_, p12) --[[ Name: get_equipment_for_id ]] --[[ Line: 309 ]]
        --[[ Upvalues: (copy 1): v_u_8 ]]
        return v_u_8:get(p12);
    end;
    v7.count = function(_) --[[ Name: count ]] --[[ Line: 313 ]]
        --[[ Upvalues: (copy 1): v_u_8 ]]
        return v_u_8:count();
    end;
    v7.get_equipmentdatabase_info = function(_) --[[ Name: get_equipmentdatabase_info ]] --[[ Line: 315 ]]
        --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_5 ]]
        local v13 = {}
        for v14, v15 in v_u_8:key_itr() do
            table.insert(v13, #v13 + 1, {
                ["equipmentid"] = v14,
                ["name"] = v15:get_name(),
                ["slot"] = v15:get_avatar_slot(),
                ["gearpower"] = v15:get_gear_power(),
                ["tier"] = v15:get_gear_tier(),
                ["craftable"] = v_u_5:singleton():contains_recipe_id_for_gear_id(v14)
            })
        end;
        return v13;
    end;
    v7.dump_gear_data = function(_) --[[ Name: dump_gear_data ]] --[[ Line: 330 ]]
        --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_2, (ref 3): v_u_4 ]]
        local v16 = ""
        for v17, v18 in v_u_8:key_itr() do
            local function _(p19, p20) --[[ Name: get_stat_display_value ]] --[[ Line: 333 ]]
                local v21 = p19:get_gear_statmodifierobj()
                if v21[p20] == nil then
                    return tostring(0);
                else
                    return tostring(v21[p20]);
                end;
            end;
            local v22 = ((("" .. tostring(v17) .. "\t") .. tostring(v18:get_name()) .. "\t") .. tostring(v_u_2:slot_to_name(v18:get_avatar_slot())) .. "\t") .. tostring(v18:get_gear_tier()) .. "\t"
            local l_ColorBlue_0 = v_u_4.Type.ColorBlue
            local v23 = v18:get_gear_statmodifierobj()
            local v24
            if v23[l_ColorBlue_0] == nil then
                v24 = tostring(0)
            else
                v24 = tostring(v23[l_ColorBlue_0])
            end;
            local v25 = v22 .. v24 .. "\t"
            local l_ColorGreen_0 = v_u_4.Type.ColorGreen
            local v26 = v18:get_gear_statmodifierobj()
            local v27
            if v26[l_ColorGreen_0] == nil then
                v27 = tostring(0)
            else
                v27 = tostring(v26[l_ColorGreen_0])
            end;
            local v28 = v25 .. v27 .. "\t"
            local l_ColorPurple_0 = v_u_4.Type.ColorPurple
            local v29 = v18:get_gear_statmodifierobj()
            local v30
            if v29[l_ColorPurple_0] == nil then
                v30 = tostring(0)
            else
                v30 = tostring(v29[l_ColorPurple_0])
            end;
            local v31 = v28 .. v30 .. "\t"
            local l_ColorRed_0 = v_u_4.Type.ColorRed
            local v32 = v18:get_gear_statmodifierobj()
            local v33
            if v32[l_ColorRed_0] == nil then
                v33 = tostring(0)
            else
                v33 = tostring(v32[l_ColorRed_0])
            end;
            local v34 = v31 .. v33 .. "\t"
            local l_ColorOrange_0 = v_u_4.Type.ColorOrange
            local v35 = v18:get_gear_statmodifierobj()
            local v36
            if v35[l_ColorOrange_0] == nil then
                v36 = tostring(0)
            else
                v36 = tostring(v35[l_ColorOrange_0])
            end;
            local v37 = v34 .. v36 .. "\t"
            local l_PerfectTime_0 = v_u_4.Type.PerfectTime
            local v38 = v18:get_gear_statmodifierobj()
            local v39
            if v38[l_PerfectTime_0] == nil then
                v39 = tostring(0)
            else
                v39 = tostring(v38[l_PerfectTime_0])
            end;
            local v40 = v37 .. v39 .. "\t"
            local l_PerfectPoints_0 = v_u_4.Type.PerfectPoints
            local v41 = v18:get_gear_statmodifierobj()
            local v42
            if v41[l_PerfectPoints_0] == nil then
                v42 = tostring(0)
            else
                v42 = tostring(v41[l_PerfectPoints_0])
            end;
            local v43 = v40 .. v42 .. "\t"
            local l_FeverFillRate_0 = v_u_4.Type.FeverFillRate
            local v44 = v18:get_gear_statmodifierobj()
            local v45
            if v44[l_FeverFillRate_0] == nil then
                v45 = tostring(0)
            else
                v45 = tostring(v44[l_FeverFillRate_0])
            end;
            local v46 = v43 .. v45 .. "\t"
            local l_FeverMultiplier_0 = v_u_4.Type.FeverMultiplier
            local v47 = v18:get_gear_statmodifierobj()
            local v48
            if v47[l_FeverMultiplier_0] == nil then
                v48 = tostring(0)
            else
                v48 = tostring(v47[l_FeverMultiplier_0])
            end;
            local v49 = v46 .. v48 .. "\t"
            local l_FeverTime_0 = v_u_4.Type.FeverTime
            local v50 = v18:get_gear_statmodifierobj()
            local v51
            if v50[l_FeverTime_0] == nil then
                v51 = tostring(0)
            else
                v51 = tostring(v50[l_FeverTime_0])
            end;
            local v52 = v49 .. v51 .. "\t"
            local l_ComboMultiplier_0 = v_u_4.Type.ComboMultiplier
            local v53 = v18:get_gear_statmodifierobj()
            local v54
            if v53[l_ComboMultiplier_0] == nil then
                v54 = tostring(0)
            else
                v54 = tostring(v53[l_ComboMultiplier_0])
            end;
            v16 = v16 .. (v52 .. v54) .. "\n"
        end;
        print("\n" .. v16)
    end;
    v7:cons()
    return v7;
end;
local v_u_55 = v6:new()
v6.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 368 ]]
    --[[ Upvalues: (copy 1): v_u_55 ]]
    return v_u_55;
end;
return v6;
