-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

local s_HttpService_0 = game:GetService("HttpService")
local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v9:require_shared(function() --[[ Line: 15 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12 ]]
    v_u_10 = require(game.ReplicatedStorage.Pets.PetUtils)
    v_u_11 = require(game.ReplicatedStorage.Avatar.PlayerBlobLoadout)
    v_u_12 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
end)
local v_u_110 = {
    ["PlayerIDInvalid"] = -9999,
    ["CurrencyType"] = {
        ["Coins"] = 0,
        ["Stars"] = 1
    },
    ["TutorialStage"] = {
        ["NewPlayer"] = 0,
        ["LegacyTutorialComplete"] = 1,
        ["TutorialSongAcquired"] = 2,
        ["TutorialComplete"] = 3
    },
    ["get_coin_currency"] = function(_, p13) --[[ Name: get_coin_currency ]] --[[ Line: 211 ]]
        return p13.CoinCurrency;
    end,
    ["set_coin_currency"] = function(_, p14, p15) --[[ Name: set_coin_currency ]] --[[ Line: 214 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        v_u_6:is_int(p15)
        v_u_6:is_true(p15 >= 0)
        p14.CoinCurrency = p15
    end,
    ["get_star_currency"] = function(_, p16) --[[ Name: get_star_currency ]] --[[ Line: 219 ]]
        return p16.StarCurrency;
    end,
    ["set_star_currency"] = function(_, p17, p18) --[[ Name: set_star_currency ]] --[[ Line: 222 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        v_u_6:is_int(p18)
        v_u_6:is_true(p18 >= 0)
        p17.StarCurrency = p18
    end,
    ["to_json"] = function(_, p19) --[[ Name: to_json ]] --[[ Line: 354 ]]
        --[[ Upvalues: (copy 1): s_HttpService_0 ]]
        return s_HttpService_0:JSONEncode(p19);
    end,
    ["update_from_obj"] = function(_, p20, p21) --[[ Name: update_from_obj ]] --[[ Line: 362 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        if p20.UserId == nil then
            error("PlayerBlob:update_from_obj json_obj.UserId is nil")
        end;
        v_u_6:is_int(p21.LastModifiedTime)
        p20.LastModifiedTime = p21.LastModifiedTime
        if typeof(p21.DataStoreWriteTime) == "number" then
            v_u_6:is_int(p21.DataStoreWriteTime)
            p20.DataStoreWriteTime = p21.DataStoreWriteTime
        end;
        p20.UserId = p21.UserId
        p20.TutorialStage = p21.TutorialStage
        p20.SongInventory = p21.SongInventory
        p20.CoinCurrency = p21.CoinCurrency
        p20.StarCurrency = p21.StarCurrency
        p20.SongShopDayInfo = p21.SongShopDayInfo
        p20.Equipped = p21.Equipped
        p20.OwnedEquipment = p21.OwnedEquipment
        for v22 = 1, #p20.OwnedEquipment do
            local l_OwnedEquipment_0 = p20.OwnedEquipment[v22]
            if l_OwnedEquipment_0.BoostUsedCount == nil then
                l_OwnedEquipment_0.BoostUsedCount = 0
            end;
            if l_OwnedEquipment_0.BoostUsedID == nil then
                l_OwnedEquipment_0.BoostUsedID = 0
            end;
        end;
        p20.GearShopDayInfo = p21.GearShopDayInfo
        p20.MissionRank = p21.MissionRank
        p20.DayMissionProgress = p21.DayMissionProgress
        p20.LastUpdatedDay = p21.LastUpdatedDay
        p20.MatchesLeft = p21.MatchesLeft
        p20.HasWarning = p21.HasWarning
        p20.Warning = p21.Warning
        v_u_6:is_bool(p21.Banned)
        p20.Banned = p21.Banned
        p20.JustLeftMatch = p21.JustLeftMatch
        p20.MatchLeavePenaltyEndTime = p21.MatchLeavePenaltyEndTime
        v_u_6:is_table(p21.CraftingMaterials)
        p20.CraftingMaterials = p21.CraftingMaterials
        p20.PlayerSettings = p21.PlayerSettings
        v_u_6:is_number(p21.CurrentTitleID)
        p20.CurrentTitleID = p21.CurrentTitleID
        p20.OwnedTitles = p21.OwnedTitles
        v_u_6:is_table(p21.WeekMissionProgress)
        p20.WeekMissionProgress = p21.WeekMissionProgress
        v_u_6:is_int(p21.BaseColor1)
        v_u_6:is_int(p21.BaseColor2)
        v_u_6:is_int(p21.BaseColor3)
        v_u_6:is_int(p21.BaseColor4)
        v_u_6:is_int(p21.FeverColor1)
        v_u_6:is_int(p21.FeverColor2)
        v_u_6:is_int(p21.FeverColor3)
        v_u_6:is_int(p21.FeverColor4)
        v_u_6:is_int(p21.FeverIcon)
        p20.BaseColor1 = p21.BaseColor1
        p20.BaseColor2 = p21.BaseColor2
        p20.BaseColor3 = p21.BaseColor3
        p20.BaseColor4 = p21.BaseColor4
        p20.FeverColor1 = p21.FeverColor1
        p20.FeverColor2 = p21.FeverColor2
        p20.FeverColor3 = p21.FeverColor3
        p20.FeverColor4 = p21.FeverColor4
        p20.FeverIcon = p21.FeverIcon
        v_u_6:is_int(p21.VIPDay)
        p20.VIPDay = p21.VIPDay
        v_u_6:is_table(p21.DanceEquipped)
        v_u_6:is_table(p21.DanceOwned)
        p20.DanceEquipped = p21.DanceEquipped
        p20.DanceOwned = p21.DanceOwned
        v_u_6:is_int(p21.ChallengePassPoints)
        v_u_6:is_int(p21.ChallengePassMonth)
        v_u_6:is_bool(p21.ChallengePassMonthActivated)
        v_u_6:is_int(p21.ChallengePassActiveTier)
        p20.ChallengePassPoints = p21.ChallengePassPoints
        p20.ChallengePassMonth = p21.ChallengePassMonth
        p20.ChallengePassMonthActivated = p21.ChallengePassMonthActivated
        p20.ChallengePassActiveTier = p21.ChallengePassActiveTier
        v_u_6:is_table(p21.MarketSales)
        p20.MarketSales = p21.MarketSales
        v_u_6:is_int(p21.SongLaunchClaimedID)
        p20.SongLaunchClaimedID = p21.SongLaunchClaimedID
        if typeof(p21.Loadouts) == "table" then
            p20.Loadouts = p21.Loadouts
        end;
        if typeof(p21.TeamBuffWeekID) == "number" then
            p20.TeamBuffWeekID = p21.TeamBuffWeekID
            p20.TeamBuffColor = p21.TeamBuffColor
            p20.TeamBuffLevel = p21.TeamBuffLevel
        end;
        if typeof(p21.ArtEvtID) == "number" then
            p20.ArtEvtID = p21.ArtEvtID
            p20.ArtEvtPoints = p21.ArtEvtPoints
            p20.ArtEvtClaimed = p21.ArtEvtClaimed
        end;
        if typeof(p21.OwnedPets) == "table" then
            p20.OwnedPets = p21.OwnedPets
        end;
        if typeof(p21.EquippedPets) == "table" then
            p20.EquippedPets = p21.EquippedPets
        end;
        if typeof(p21.LoginDayCount) == "number" then
            p20.LoginDayCount = p21.LoginDayCount
        end;
        if typeof(p21.LoginDayID) == "number" then
            p20.LoginDayID = p21.LoginDayID
        end;
        if typeof(p21.LoginMonthID) == "number" then
            p20.LoginMonthID = p21.LoginMonthID
        end;
        if typeof(p21.TeamBonusWeekID) == "number" then
            p20.TeamBonusWeekID = p21.TeamBonusWeekID
        end;
        if typeof(p21.TeamBonusClaimed) == "number" then
            p20.TeamBonusClaimed = p21.TeamBonusClaimed
        end;
        if typeof(p21.TeamContCapDaySongMission) == "number" then
            p20.TeamContCapDaySongMission = p21.TeamContCapDaySongMission
        end;
        if typeof(p21.TeamContCapDaySongMissionDayID) == "number" then
            p20.TeamContCapDaySongMissionDayID = p21.TeamContCapDaySongMissionDayID
        end;
        if typeof(p21.CollectionInfoJson) == "string" then
            p20.CollectionInfoJson = p21.CollectionInfoJson
        end;
        if typeof(p21.GSLvl) == "number" then
            p20.GSLvl = p21.GSLvl
        end;
        if typeof(p21.LSLvl) == "number" then
            p20.LSLvl = p21.LSLvl
        end;
        if typeof(p21.CPV2Points) == "number" then
            p20.CPV2Points = p21.CPV2Points
        end;
        if typeof(p21.CPV2MonthID) == "number" then
            p20.CPV2MonthID = p21.CPV2MonthID
        end;
        if typeof(p21.CPV2MonthUpgradeToVIP) == "boolean" then
            p20.CPV2MonthUpgradeToVIP = p21.CPV2MonthUpgradeToVIP
        end;
        if typeof(p21.CPV2DayID) == "number" then
            p20.CPV2DayID = p21.CPV2DayID
        end;
        if typeof(p21.CPV2DayFlags) == "number" then
            p20.CPV2DayFlags = p21.CPV2DayFlags
        end;
        if typeof(p21.CPV2WeekID) == "number" then
            p20.CPV2WeekID = p21.CPV2WeekID
        end;
        if typeof(p21.CPV2WeekFlags) == "number" then
            p20.CPV2WeekFlags = p21.CPV2WeekFlags
        end;
        if typeof(p21.CPV2StandardClaimedTier) == "number" then
            p20.CPV2StandardClaimedTier = p21.CPV2StandardClaimedTier
        end;
        if typeof(p21.CPV2VIPClaimedTier) == "number" then
            p20.CPV2VIPClaimedTier = p21.CPV2VIPClaimedTier
        end;
        if typeof(p21.MissionMPRewardFlag) == "number" then
            p20.MissionMPRewardFlag = p21.MissionMPRewardFlag
        end;
        if typeof(p21.MissionMPRewardDayID) == "number" then
            p20.MissionMPRewardDayID = p21.MissionMPRewardDayID
        end;
    end,
    ["validate_with_dayid_weekid"] = function(_, p23, p_u_24, p_u_25) --[[ Name: validate_with_dayid_weekid ]] --[[ Line: 538 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (ref 3): v_u_10, (copy 4): v_u_1, (ref 5): v_u_11 ]]
        local v_u_26 = false
        local v_u_27 = v_u_3:new()
        v_u_2:remove_if(v_u_2:new(p23.DayMissionProgress), function(p28) --[[ Line: 546 ]]
            --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_3, (copy 3): v_u_27, (ref 4): v_u_26 ]]
            local v29 = false
            if p28.DayID == nil then
                p28.DayID = p_u_24
                v_u_3:counter_increment(v_u_27, "DayMissionProgress_NoDayID", 1)
            end;
            if p28.DayID ~= p_u_24 then
                v29 = true
                v_u_26 = true
                v_u_3:counter_increment(v_u_27, "DayMissionProgress_MismatchDayID", 1)
                v_u_27:add("DayID", p28.DayID)
            end;
            return v29;
        end)
        v_u_2:remove_if(v_u_2:new(p23.WeekMissionProgress), function(p30) --[[ Line: 566 ]]
            --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_26, (ref 3): v_u_3, (copy 4): v_u_27 ]]
            local v31 = false
            if p30.WeekID == nil then
                p30.WeekID = p_u_25
            end;
            if p30.WeekID ~= p_u_25 then
                v31 = true
                v_u_26 = true
                v_u_3:counter_increment(v_u_27, "WeekMissionProgress_MismatchWeekID", 1)
                v_u_27:add("WeekID", p30.WeekID)
            end;
            return v31;
        end)
        v_u_2:remove_if(v_u_2:new(p23.SongShopDayInfo), function(p32) --[[ Line: 585 ]]
            --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_26 ]]
            local v33 = false
            if p32.DayID == nil then
                p32.DayID = p_u_24
            end;
            if p32.DayID ~= p_u_24 then
                v33 = true
                v_u_26 = true
            end;
            return v33;
        end)
        v_u_2:remove_if(v_u_2:new(p23.GearShopDayInfo), function(p34) --[[ Line: 602 ]]
            --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_26 ]]
            local v35 = false
            if p34.DayID == nil then
                p34.DayID = p_u_24
            end;
            if p34.DayID ~= p_u_24 then
                v35 = true
                v_u_26 = true
            end;
            return v35;
        end)
        local v36
        if v_u_10 then
            v36 = v_u_10:playerblob_validate_with_dayid_weekid(p23, p_u_24, p_u_25, v_u_27) and true or v_u_26
        else
            v_u_1:warnf("PlayerBlob:validate_with_dayid_weekid PetUtils is nil")
            v36 = v_u_26
        end;
        if v_u_11 then
            v36 = v_u_11:playerblob_validate_with_dayid_weekid(p23, p_u_24, p_u_25, v_u_27) and true or v36
        else
            v_u_1:warnf("PlayerBlob:validate_with_dayid_weekid PlayerBlobLoadout is nil")
        end;
        return v36, v_u_27;
    end,
    ["SongInventorySort_DifficultyAsc"] = 1,
    ["SongInventorySort_DifficultyDesc"] = 2,
    ["SongInventorySort_OwnedCountAsc"] = 3,
    ["SongInventorySort_OwnedCountDesc"] = 4,
    ["SongInventorySort_AlphabeticalAsc"] = 5,
    ["SongInventorySort_AlphabeticalDesc"] = 6,
    ["song_inventory_element_values"] = function(_, p37) --[[ Name: song_inventory_element_values ]] --[[ Line: 714 ]]
        return p37.Key, p37.Count;
    end,
    ["add_song"] = function(_, p38, p39) --[[ Name: add_song ]] --[[ Line: 718 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_4, (copy 3): v_u_8 ]]
        v_u_6:is_true(v_u_4:singleton():contains_key(p39))
        v_u_6:is_true(v_u_4:singleton():key_get_audiomod(p39) ~= v_u_8.Easy)
        for v40 = 1, #p38.SongInventory do
            local l_SongInventory_0 = p38.SongInventory[v40]
            if l_SongInventory_0.Key == p39 then
                l_SongInventory_0.Count = l_SongInventory_0.Count + 1
                return;
            end;
        end;
        table.insert(p38.SongInventory, {
            ["Key"] = p39,
            ["Count"] = 1
        })
    end,
    ["remove_songs"] = function(_, p41, p42, p43) --[[ Name: remove_songs ]] --[[ Line: 732 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1 ]]
        v_u_6:is_int(p43)
        v_u_6:is_true(p43 >= 0)
        for v44 = 1, #p41.SongInventory do
            local l_SongInventory_1 = p41.SongInventory[v44]
            if l_SongInventory_1.Key == p42 then
                local v45 = l_SongInventory_1.Count - p43
                if v45 < 0 then
                    v_u_1:errf("PlayerBlob:remove_songs(%d,%d) count_post(%d)", p42, p43, v45)
                end;
                if v45 <= 0 then
                    table.remove(p41.SongInventory, v44)
                end;
                l_SongInventory_1.Count = v45
                return;
            end;
        end;
    end,
    ["get_song_key_owned_count"] = function(_, p46, p47) --[[ Name: get_song_key_owned_count ]] --[[ Line: 756 ]]
        for v48 = 1, #p46.SongInventory do
            local l_SongInventory_2 = p46.SongInventory[v48]
            if l_SongInventory_2.Key == p47 then
                return l_SongInventory_2.Count;
            end;
        end;
        return 0;
    end,
    ["get_count_for_song_shop_saleid"] = function(_, p49, p50) --[[ Name: get_count_for_song_shop_saleid ]] --[[ Line: 786 ]]
        local v51 = 0
        for v52 = 1, #p49.SongShopDayInfo do
            v53 = p49.SongShopDayInfo[v52]
            if v53.SaleId == p50 then
                -- -- -- -- -- -- ::l5:: (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto)
                if v53 then
                    v51 = v53.Count
                end;
                return v51;
            end;
        end;
        local v53 = nil
        break;
    end,
    ["add_count_for_song_shop_saleid"] = function(_, p_u_54, p_u_55, p_u_56, p57) --[[ Name: add_count_for_song_shop_saleid ]] --[[ Line: 795 ]]
        local function _() --[[ Name: get_create_song_shop_saleobject_for_saleid ]] --[[ Line: 796 ]]
            --[[ Upvalues: (copy 1): p_u_54, (copy 2): p_u_55, (copy 3): p_u_56 ]]
            local v58 = p_u_54
            local v59 = p_u_55
            for v60 = 1, #v58.SongShopDayInfo do
                v62 = v58.SongShopDayInfo[v60]
                if v62.SaleId == v59 then
                    -- -- -- -- -- -- ::l5:: (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto)
                    if v62 ~= nil then
                        return v62;
                    end;
                    local v61 = {
                        ["SaleId"] = p_u_55,
                        ["Count"] = 0,
                        ["DayID"] = p_u_56
                    }
                    table.insert(p_u_54.SongShopDayInfo, v61)
                    return v61;
                end;
            end;
            local v62 = nil
            break;
        end;
        for v63 = 1, #p_u_54.SongShopDayInfo do
            v64 = p_u_54.SongShopDayInfo[v63]
            if v64.SaleId == p_u_55 then
                break;
            end;
        end;
        local v64 = nil
        -- -- -- -- -- -- ::l5:: (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto)
        if v64 == nil then
            v64 = {
                ["SaleId"] = p_u_55,
                ["Count"] = 0,
                ["DayID"] = p_u_56
            }
            table.insert(p_u_54.SongShopDayInfo, v64)
        end;
        v64.Count = v64.Count + p57
    end,
    ["get_count_for_gear_shop_saleid"] = function(_, p65, p66) --[[ Name: get_count_for_gear_shop_saleid ]] --[[ Line: 822 ]]
        local v67 = 0
        for v68 = 1, #p65.GearShopDayInfo do
            v69 = p65.GearShopDayInfo[v68]
            if v69.SaleId == p66 then
                -- -- -- -- -- -- ::l5:: (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto)
                if v69 then
                    v67 = v69.Count
                end;
                return v67;
            end;
        end;
        local v69 = nil
        break;
    end,
    ["add_count_for_gear_shop_saleid"] = function(_, p_u_70, p_u_71, p_u_72, p73) --[[ Name: add_count_for_gear_shop_saleid ]] --[[ Line: 831 ]]
        local function _() --[[ Name: get_create_gear_shop_saleobject_for_saleid ]] --[[ Line: 832 ]]
            --[[ Upvalues: (copy 1): p_u_70, (copy 2): p_u_71, (copy 3): p_u_72 ]]
            local v74 = p_u_70
            local v75 = p_u_71
            for v76 = 1, #v74.GearShopDayInfo do
                v78 = v74.GearShopDayInfo[v76]
                if v78.SaleId == v75 then
                    -- -- -- -- -- -- ::l5:: (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto)
                    if v78 ~= nil then
                        return v78;
                    end;
                    local v77 = {
                        ["SaleId"] = p_u_71,
                        ["Count"] = 0,
                        ["DayID"] = p_u_72
                    }
                    table.insert(p_u_70.GearShopDayInfo, v77)
                    return v77;
                end;
            end;
            local v78 = nil
            break;
        end;
        for v79 = 1, #p_u_70.GearShopDayInfo do
            v80 = p_u_70.GearShopDayInfo[v79]
            if v80.SaleId == p_u_71 then
                break;
            end;
        end;
        local v80 = nil
        -- -- -- -- -- -- ::l5:: (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto) (Possible bug with goto)
        if v80 == nil then
            v80 = {
                ["SaleId"] = p_u_71,
                ["Count"] = 0,
                ["DayID"] = p_u_72
            }
            table.insert(p_u_70.GearShopDayInfo, v80)
        end;
        v80.Count = v80.Count + p73
    end,
    ["is_banned"] = function(_, _) --[[ Name: is_banned ]] --[[ Line: 847 ]]
        return false;
    end,
    ["has_warning"] = function(_, _) --[[ Name: has_warning ]] --[[ Line: 852 ]]
        return false;
    end,
    ["get_warning"] = function(_, p81) --[[ Name: get_warning ]] --[[ Line: 856 ]]
        return p81.Warning;
    end,
    ["set_warning"] = function(_, p82, p83, p84) --[[ Name: set_warning ]] --[[ Line: 857 ]]
        p82.HasWarning = p83
        p82.Warning = p84
    end,
    ["get_matches_left"] = function(_, p85) --[[ Name: get_matches_left ]] --[[ Line: 862 ]]
        return p85.MatchesLeft;
    end,
    ["set_matches_left"] = function(_, p86, p87) --[[ Name: set_matches_left ]] --[[ Line: 863 ]]
        p86.MatchesLeft = p87
    end,
    ["get_just_left_match"] = function(_, p88) --[[ Name: get_just_left_match ]] --[[ Line: 867 ]]
        return p88.JustLeftMatch;
    end,
    ["set_just_left_match"] = function(_, p89, p90) --[[ Name: set_just_left_match ]] --[[ Line: 868 ]]
        p89.JustLeftMatch = p90
    end,
    ["get_match_leave_penalty_end_time"] = function(_, p91) --[[ Name: get_match_leave_penalty_end_time ]] --[[ Line: 870 ]]
        return p91.MatchLeavePenaltyEndTime;
    end,
    ["set_match_leave_penalty_end_time"] = function(_, p92, p93) --[[ Name: set_match_leave_penalty_end_time ]] --[[ Line: 871 ]]
        p92.MatchLeavePenaltyEndTime = p93
    end,
    ["is_match_leaving_penalized"] = function(_, _, _) --[[ Name: is_match_leaving_penalized ]] --[[ Line: 872 ]]
        return false;
    end,
    ["get_player_settings_str"] = function(_, p94) --[[ Name: get_player_settings_str ]] --[[ Line: 879 ]]
        return p94.PlayerSettings;
    end,
    ["set_player_settings_str"] = function(_, p95, p96) --[[ Name: set_player_settings_str ]] --[[ Line: 883 ]]
        p95.PlayerSettings = p96
    end,
    ["set_title_id"] = function(_, p97, p98) --[[ Name: set_title_id ]] --[[ Line: 889 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        v_u_6:is_number(p98)
        p97.CurrentTitleID = p98
    end,
    ["get_title_id"] = function(_, p99) --[[ Name: get_title_id ]] --[[ Line: 894 ]]
        return p99.CurrentTitleID;
    end,
    ["owns_title_id"] = function(_, p100, p101) --[[ Name: owns_title_id ]] --[[ Line: 897 ]]
        if p101 == 0 then
            return true;
        end;
        for v102 = 1, #p100.OwnedTitles do
            if p100.OwnedTitles[v102].ID == p101 then
                return true;
            end;
        end;
        return false;
    end,
    ["get_owned_title_id_set"] = function(_, p103) --[[ Name: get_owned_title_id_set ]] --[[ Line: 907 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        local v104 = v_u_3:new()
        for v105 = 1, #p103.OwnedTitles do
            v104:add_set(p103.OwnedTitles[v105].ID)
        end;
        return v104;
    end,
    ["add_title"] = function(_, p106, p107) --[[ Name: add_title ]] --[[ Line: 915 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1 ]]
        if v_u_5:singleton():get_title_for_id(p107) == nil then
            v_u_1:errf("PlayerBlob:add_title not found title_id(%s)", (tostring(p107)))
        end;
        local l_OwnedTitles_0 = p106.OwnedTitles
        for v108 = 1, #l_OwnedTitles_0 do
            if l_OwnedTitles_0[v108].ID == p107 then
                return false;
            end;
        end;
        l_OwnedTitles_0[#l_OwnedTitles_0 + 1] = {
            ["ID"] = p107
        }
        return true;
    end,
    ["get_tester_title_id"] = function(_) --[[ Name: get_tester_title_id ]] --[[ Line: 950 ]]
        return 16;
    end,
    ["get_user_id"] = function(_, p109) --[[ Name: get_user_id ]] --[[ Line: 964 ]]
        return p109.UserId;
    end
}
v_u_110.currency_type_to_string = function(_, p111) --[[ Name: currency_type_to_string ]] --[[ Line: 171 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    return p111 == v_u_110.CurrencyType.Coins and "Coins" or (p111 == v_u_110.CurrencyType.Stars and "Stars" or "?");
end;
v_u_110.currency_type_get_image = function(_, p112) --[[ Name: currency_type_get_image ]] --[[ Line: 180 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    return p112 == v_u_110.CurrencyType.Coins and "rbxassetid://818988511" or "rbxassetid://818988515";
end;
v_u_110.currency_type_render_icon = function(_, p113, p114) --[[ Name: currency_type_render_icon ]] --[[ Line: 187 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    p114.Image = v_u_110:currency_type_get_image(p113)
end;
v_u_110.get_currency_type_amount = function(_, p115, p116) --[[ Name: get_currency_type_amount ]] --[[ Line: 191 ]]
    --[[ Upvalues: (copy 1): v_u_110, (copy 2): v_u_1 ]]
    if p116 == v_u_110.CurrencyType.Coins then
        return v_u_110:get_coin_currency(p115);
    end;
    if p116 == v_u_110.CurrencyType.Stars then
        return v_u_110:get_star_currency(p115);
    end;
    v_u_1:errf("PlayerBlob:get_currency_type_amount: invalid currency type %s", (tostring(p116)))
end;
v_u_110.set_currency_type_amount = function(_, p117, p118, p119) --[[ Name: set_currency_type_amount ]] --[[ Line: 201 ]]
    --[[ Upvalues: (copy 1): v_u_110, (copy 2): v_u_1 ]]
    if p118 == v_u_110.CurrencyType.Coins then
        v_u_110:set_coin_currency(p117, p119)
        return;
    elseif p118 == v_u_110.CurrencyType.Stars then
        v_u_110:set_star_currency(p117, p119)
    else
        v_u_1:errf("PlayerBlob:set_currency_type_amount: invalid currency type %s", (tostring(p118)))
    end;
end;
v_u_110.add_currency_type = function(_, p120, p121, p122) --[[ Name: add_currency_type ]] --[[ Line: 228 ]]
    --[[ Upvalues: (copy 1): v_u_110, (copy 2): v_u_1 ]]
    if p121 == v_u_110.CurrencyType.Coins then
        v_u_110:add_coin_currency(p120, p122)
        return;
    elseif p121 == v_u_110.CurrencyType.Stars then
        v_u_110:add_star_currency(p120, p122)
    else
        v_u_1:errf("PlayerBlob:add_currency_type: invalid currency type %s", (tostring(p121)))
    end;
end;
v_u_110.add_coin_currency = function(_, p123, p124) --[[ Name: add_coin_currency ]] --[[ Line: 237 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    v_u_110:set_coin_currency(p123, v_u_110:get_coin_currency(p123) + p124)
end;
v_u_110.add_star_currency = function(_, p125, p126) --[[ Name: add_star_currency ]] --[[ Line: 240 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    v_u_110:set_star_currency(p125, v_u_110:get_star_currency(p125) + p126)
end;
v_u_110.new = function(_) --[[ Name: new ]] --[[ Line: 244 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    return {
        ["LastModifiedTime"] = 0,
        ["DataStoreWriteTime"] = 0,
        ["UserId"] = 0,
        ["TutorialStage"] = v_u_110.TutorialStage.NewPlayer,
        ["SongInventory"] = {},
        ["CoinCurrency"] = 0,
        ["StarCurrency"] = 0,
        ["LastUpdatedDay"] = 0,
        ["SongShopDayInfo"] = {},
        ["Equipped"] = {},
        ["OwnedEquipment"] = {},
        ["GearShopDayInfo"] = {},
        ["MissionRank"] = 0,
        ["DayMissionProgress"] = {},
        ["MatchesLeft"] = 0,
        ["HasWarning"] = false,
        ["Warning"] = "",
        ["Banned"] = false,
        ["JustLeftMatch"] = false,
        ["MatchLeavePenaltyEndTime"] = 0,
        ["CraftingMaterials"] = {},
        ["PlayerSettings"] = "",
        ["CurrentTitleID"] = 0,
        ["OwnedTitles"] = {},
        ["WeekMissionProgress"] = {},
        ["BaseColor1"] = 1303294,
        ["BaseColor2"] = 1303294,
        ["BaseColor3"] = 1303294,
        ["BaseColor4"] = 1303294,
        ["FeverColor1"] = 16774239,
        ["FeverColor2"] = 16774239,
        ["FeverColor3"] = 16774239,
        ["FeverColor4"] = 16774239,
        ["FeverIcon"] = 0,
        ["VIPDay"] = 0,
        ["DanceEquipped"] = {},
        ["DanceOwned"] = {},
        ["ChallengePassPoints"] = 0,
        ["ChallengePassMonth"] = 0,
        ["ChallengePassMonthActivated"] = false,
        ["ChallengePassActiveTier"] = 0,
        ["MarketSales"] = {},
        ["SongLaunchClaimedID"] = 0,
        ["Loadouts"] = {},
        ["TeamBuffWeekID"] = 0,
        ["TeamBuffColor"] = 0,
        ["TeamBuffLevel"] = 0,
        ["ArtEvtID"] = 0,
        ["ArtEvtPoints"] = 0,
        ["ArtEvtClaimed"] = 0,
        ["OwnedPets"] = {},
        ["EquippedPets"] = {},
        ["LoginDayCount"] = 0,
        ["LoginDayID"] = 0,
        ["LoginMonthID"] = 0,
        ["TeamBonusWeekID"] = 0,
        ["TeamBonusClaimed"] = 0,
        ["TeamContCapDaySongMission"] = 0,
        ["TeamContCapDaySongMissionDayID"] = 0,
        ["CollectionInfoJson"] = "",
        ["GSLvl"] = 0,
        ["LSLvl"] = 0,
        ["CPV2Points"] = 0,
        ["CPV2MonthID"] = 0,
        ["CPV2MonthUpgradeToVIP"] = false,
        ["CPV2DayID"] = 0,
        ["CPV2DayFlags"] = 0,
        ["CPV2WeekID"] = 0,
        ["CPV2WeekFlags"] = 0,
        ["CPV2StandardClaimedTier"] = 0,
        ["CPV2VIPClaimedTier"] = 0,
        ["MissionMPRewardFlag"] = 0,
        ["MissionMPRewardDayID"] = 0
    };
end;
local v_u_127 = v_u_110:new()
v_u_110.get_default_playerblob = function(_) --[[ Name: get_default_playerblob ]] --[[ Line: 350 ]]
    --[[ Upvalues: (copy 1): v_u_127 ]]
    return v_u_127;
end;
v_u_110.update_from_json = function(_, p128, p129) --[[ Name: update_from_json ]] --[[ Line: 358 ]]
    --[[ Upvalues: (copy 1): v_u_110, (copy 2): s_HttpService_0 ]]
    v_u_110:update_from_obj(p128, s_HttpService_0:JSONDecode(p129))
end;
v_u_110.song_inventory_key_to_owned_count_dict = function(_, p130) --[[ Name: song_inventory_key_to_owned_count_dict ]] --[[ Line: 645 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_110, (copy 3): v_u_4 ]]
    local v131 = v_u_3:new()
    for v132 = 1, #p130.SongInventory do
        local v133, v134 = v_u_110:song_inventory_element_values(p130.SongInventory[v132])
        if v_u_4:singleton():contains_key(v133) and v134 > 0 then
            v131:add(v133, v134)
        end;
    end;
    return v131;
end;
v_u_110.song_inventory_songids_set = function(_, p135) --[[ Name: song_inventory_songids_set ]] --[[ Line: 656 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_110, (copy 3): v_u_4 ]]
    local v136 = v_u_3:new()
    for v137 = 1, #p135.SongInventory do
        local v138, v139 = v_u_110:song_inventory_element_values(p135.SongInventory[v137])
        if v_u_4:singleton():contains_key(v138) and v139 > 0 then
            v136:add(v138, true)
        end;
    end;
    return v136;
end;
v_u_110.song_inventory_songids_list = function(_, p140) --[[ Name: song_inventory_songids_list ]] --[[ Line: 667 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    return v_u_110:song_inventory_songids_set(p140):key_list();
end;
v_u_110.sort_playerblob_songids_list = function(_, p_u_141, p142, p143) --[[ Name: sort_playerblob_songids_list ]] --[[ Line: 671 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_110, (copy 3): v_u_4, (copy 4): v_u_1 ]]
    local v_u_144 = v_u_3:new()
    local function _(p145) --[[ Name: get_owned_count_for_key ]] --[[ Line: 673 ]]
        --[[ Upvalues: (copy 1): v_u_144, (ref 2): v_u_110, (copy 3): p_u_141 ]]
        if v_u_144:contains(p145) then
            return v_u_144:get(p145);
        end;
        local v146 = v_u_110:get_song_key_owned_count(p_u_141, p145)
        v_u_144:add(p145, v146)
        return v146;
    end;
    if p143 == v_u_110.SongInventorySort_DifficultyAsc then
        p142:sort(function(p147, p148) --[[ Line: 681 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return v_u_4:singleton():get_difficulty_for_key(p148) - v_u_4:singleton():get_difficulty_for_key(p147);
        end)
        return p142;
    elseif p143 == v_u_110.SongInventorySort_DifficultyDesc then
        p142:sort(function(p149, p150) --[[ Line: 685 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return v_u_4:singleton():get_difficulty_for_key(p149) - v_u_4:singleton():get_difficulty_for_key(p150);
        end)
        return p142;
    elseif p143 == v_u_110.SongInventorySort_OwnedCountAsc then
        p142:sort(function(p151, p152) --[[ Line: 689 ]]
            --[[ Upvalues: (copy 1): v_u_144, (ref 2): v_u_110, (copy 3): p_u_141 ]]
            local v153
            if v_u_144:contains(p152) then
                v153 = v_u_144:get(p152)
            else
                v153 = v_u_110:get_song_key_owned_count(p_u_141, p152)
                v_u_144:add(p152, v153)
            end;
            local v154
            if v_u_144:contains(p151) then
                v154 = v_u_144:get(p151)
            else
                v154 = v_u_110:get_song_key_owned_count(p_u_141, p151)
                v_u_144:add(p151, v154)
            end;
            return v153 - v154;
        end)
        return p142;
    elseif p143 == v_u_110.SongInventorySort_OwnedCountDesc then
        p142:sort(function(p155, p156) --[[ Line: 693 ]]
            --[[ Upvalues: (copy 1): v_u_144, (ref 2): v_u_110, (copy 3): p_u_141 ]]
            local v157
            if v_u_144:contains(p155) then
                v157 = v_u_144:get(p155)
            else
                v157 = v_u_110:get_song_key_owned_count(p_u_141, p155)
                v_u_144:add(p155, v157)
            end;
            local v158
            if v_u_144:contains(p156) then
                v158 = v_u_144:get(p156)
            else
                v158 = v_u_110:get_song_key_owned_count(p_u_141, p156)
                v_u_144:add(p156, v158)
            end;
            return v157 - v158;
        end)
        return p142;
    elseif p143 == v_u_110.SongInventorySort_AlphabeticalAsc then
        p142:sort(function(p159, p160) --[[ Line: 697 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return string.lower(v_u_4:singleton():get_title_for_key(p159)) < string.lower(v_u_4:singleton():get_title_for_key(p160));
        end)
        return p142;
    elseif p143 == v_u_110.SongInventorySort_AlphabeticalDesc then
        p142:sort(function(p161, p162) --[[ Line: 701 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return string.lower(v_u_4:singleton():get_title_for_key(p161)) > string.lower(v_u_4:singleton():get_title_for_key(p162));
        end)
        return p142;
    else
        v_u_1:warnf("PlayerBlob:sort_playerblob_songids_list unknown sort type(%s)", (tostring(p143)))
        return p142;
    end;
end;
v_u_110.song_inventory_sorted_view = function(_, p163, p164) --[[ Name: song_inventory_sorted_view ]] --[[ Line: 710 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    return v_u_110:sort_playerblob_songids_list(p163, v_u_110:song_inventory_songids_list(p163), p164);
end;
v_u_110.get_owned_songs = function(_, p165) --[[ Name: get_owned_songs ]] --[[ Line: 752 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    return v_u_110:song_inventory_songids_list(p165);
end;
v_u_110.get_song_key_owned_count_including_collection = function(_, p166, p167, p168) --[[ Name: get_song_key_owned_count_including_collection ]] --[[ Line: 765 ]]
    --[[ Upvalues: (copy 1): v_u_110, (ref 2): v_u_12 ]]
    local v169 = v_u_110:get_song_key_owned_count(p166, p167)
    if v_u_12:get_playerblob_songkey_in_collection(p166, p167, p168) == true then
        v169 = v169 + 1
    end;
    return v169;
end;
local function _(p170, p171) --[[ Name: playerblob_get_song_shop_saleobject_for_saleid ]] --[[ Line: 776 ]]
    for v172 = 1, #p170.SongShopDayInfo do
        local l_SongShopDayInfo_0 = p170.SongShopDayInfo[v172]
        if l_SongShopDayInfo_0.SaleId == p171 then
            return l_SongShopDayInfo_0;
        end;
    end;
    return nil;
end;
local function _(p173, p174) --[[ Name: playerblob_get_gear_shop_saleobject_for_saleid ]] --[[ Line: 812 ]]
    for v175 = 1, #p173.GearShopDayInfo do
        local l_GearShopDayInfo_0 = p173.GearShopDayInfo[v175]
        if l_GearShopDayInfo_0.SaleId == p174 then
            return l_GearShopDayInfo_0;
        end;
    end;
    return nil;
end;
v_u_110.is_default_title_equipped = function(_, p176) --[[ Name: is_default_title_equipped ]] --[[ Line: 895 ]]
    --[[ Upvalues: (copy 1): v_u_110, (copy 2): v_u_5 ]]
    return v_u_110:get_title_id(p176) == v_u_5:singleton():get_default_title_id();
end;
v_u_110.is_tester_status = function(_, p177) --[[ Name: is_tester_status ]] --[[ Line: 954 ]]
    --[[ Upvalues: (copy 1): v_u_110 ]]
    local v178 = v_u_110:owns_title_id(p177, 16)
    if v178 then
        v178 = v_u_110:get_title_id(p177) == v_u_110:get_tester_title_id()
    end;
    return v178;
end;
v_u_110.err_if_banned = function(_, p179) --[[ Name: err_if_banned ]] --[[ Line: 958 ]]
    --[[ Upvalues: (copy 1): v_u_110, (copy 2): v_u_1, (copy 3): v_u_7 ]]
    if v_u_110:is_banned(p179) then
        v_u_1:errf("PlayerBlob:err_if_banned player(%s)", v_u_7:num_string(v_u_110:get_user_id(p179)))
    end;
end;
return v_u_110;
