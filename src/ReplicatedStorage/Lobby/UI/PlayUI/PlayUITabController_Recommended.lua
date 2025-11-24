-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_4 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITab)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_11 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v_u_13 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_16 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_Shared)
local l_RecommendationType_0 = v_u_16.RecommendationType
local l_SongRecommendation_0 = v_u_16.SongRecommendation
local l_ListElement_0 = v_u_16.ListElement
local v17 = {}
local v_u_18 = false
local v_u_19 = v_u_16.AudioModFilterComponent:create_filter_state()
local v_u_20 = v_u_16.FilterColorComponent:create_filter_state()
v17.new = function(_, p_u_21, p_u_22, p_u_23) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_18, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_15, (copy 6): v_u_5, (copy 7): l_ListElement_0, (copy 8): v_u_6, (copy 9): v_u_7, (copy 10): v_u_16, (copy 11): v_u_19, (copy 12): v_u_20, (copy 13): v_u_2, (copy 14): v_u_3, (copy 15): v_u_11, (copy 16): v_u_12, (copy 17): v_u_8, (copy 18): v_u_14, (copy 19): v_u_13, (copy 20): l_SongRecommendation_0, (copy 21): l_RecommendationType_0, (copy 22): v_u_10 ]]
    local v_u_24 = v_u_4.ControllerBase:new()
    v_u_24.filter_playable_only = function(_) --[[ Name: filter_playable_only ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    local v_u_25 = v_u_1:new()
    local v_u_26 = v_u_1:new()
    local v_u_27 = v_u_1:new()
    local v_u_28 = nil
    local v_u_29 = nil
    v_u_24.get_recommended_list = function(_) --[[ Name: get_recommended_list ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = false
    local function f_reroll_random_easy_mode_songkey() --[[ Name: reroll_random_easy_mode_songkey ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_9, (ref 3): v_u_15, (copy 4): p_u_21, (ref 5): v_u_32, (ref 6): v_u_31 ]]
        v_u_30 = v_u_9:singleton():get_easymode_keys_set():key_list():random()
        local v33, v34 = v_u_15:is_event_active(p_u_21._player_blob_manager:get_day_event_list())
        v_u_32 = v33
        if v_u_32 then
            v_u_31 = v_u_15:get_playable_song_set(v34):key_list():random()
        end;
    end;
    f_reroll_random_easy_mode_songkey()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_1, (ref 3): v_u_5, (copy 4): p_u_22, (ref 5): l_ListElement_0, (copy 6): p_u_21, (copy 7): v_u_24, (ref 8): v_u_6, (ref 9): v_u_7, (copy 10): v_u_25, (ref 11): v_u_18, (copy 12): v_u_26, (ref 13): v_u_28, (ref 14): v_u_16, (ref 15): v_u_19, (ref 16): v_u_29, (ref 17): v_u_20 ]]
        local l_RecommendedTabItems_0 = p_u_23.RecommendedTabItems
        local l_Proto_0 = l_RecommendedTabItems_0.Proto
        l_Proto_0.MainSurface.SurfaceGui.Enabled = true
        l_Proto_0.SelectButton.SurfaceGui.Enabled = true
        l_Proto_0.SongImageButton.SurfaceGui.Enabled = true
        l_Proto_0.Parent = nil
        for _, v35 in v_u_1:new():push_back_table_list({
            l_RecommendedTabItems_0.Anchor1,
            l_RecommendedTabItems_0.Anchor2,
            l_RecommendedTabItems_0.Anchor3,
            l_RecommendedTabItems_0.Anchor4
        }):key_itr() do
            v35.Parent = nil
            local v36 = l_Proto_0:Clone()
            v36.Parent = l_RecommendedTabItems_0
            v36:SetPrimaryPartCFrame(v35.CFrame)
            local v37 = v_u_5:new(p_u_22, p_u_23.PrimaryPart, v36.PrimaryPart):set_default_sgui()
            local v_u_38 = nil
            v_u_38 = l_ListElement_0:new(p_u_21, v_u_24, v36, v37, p_u_22:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(v37, v36.PrimaryPart, v36.SelectButton), p_u_21._spui, function() --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (ref 3): v_u_38 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_38:on_select_button_pressed()
            end)):set_auto_zoffset_behaviour(true), p_u_22:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(v37, v36.PrimaryPart, v36.SongImageButton), p_u_21._spui, function() --[[ Line: 102 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (ref 3): v_u_38 ]]
                p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_38:on_song_button_pressed()
            end)):set_auto_zoffset_behaviour(true))
            v_u_25:push_back(v_u_38)
            v_u_38:set_visible(false)
        end;
        local v39 = p_u_23.FilterButtonProtos.FilterPlayableOnlyButton:Clone()
        v39.Parent = l_RecommendedTabItems_0
        local v_u_40 = nil
        local v41 = p_u_22:add_cycle_element(p_u_21, 1, v_u_6:new(v_u_5:new(p_u_22, p_u_23.PrimaryPart, v39), p_u_21._spui, function() --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_7, (ref 3): v_u_18, (ref 4): v_u_40, (ref 5): v_u_24, (ref 6): p_u_22 ]]
            p_u_21._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_18 = not v_u_18
            v_u_40:set_toggle(v_u_18)
            v_u_24:fill_recommended_list(v_u_24:get_recommended_list())
            p_u_22:reset_page()
            p_u_22:refresh_current_page()
        end))
        v_u_40 = v_u_6:button_bind_anim_toggle(v41, function() --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): p_u_22 ]]
            return p_u_22:get_alpha();
        end)
        v_u_40:set_toggle(v_u_18)
        v_u_26:push_back(v41)
        v_u_28 = v_u_16.AudioModFilterComponent:create_audiomod_filter_buttons(p_u_21, p_u_22, p_u_23.PrimaryPart, v_u_19, l_RecommendedTabItems_0, p_u_23.FilterButtonProtos.EasyModeButton, p_u_23.FilterButtonProtos.NormalModeButton, p_u_23.FilterButtonProtos.HardModeButton, function(p42) --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26:push_back(p42)
        end, function() --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            v_u_24:fill_recommended_list(v_u_24:get_recommended_list())
        end)
        v_u_29 = v_u_16.FilterColorComponent:create_filter_button(p_u_21, p_u_22, p_u_23, p_u_23.FilterButtonProtos.ColorFilterButton, v_u_20, function(p43) --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26:push_back(p43)
        end, function() --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_24 ]]
            v_u_29:update_state()
            v_u_24:fill_recommended_list(v_u_24:get_recommended_list())
        end)
        v_u_29:update_state()
    end;
    v_u_24.on_clear_filter = function(_) --[[ Name: on_clear_filter ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_19, (ref 3): v_u_28, (ref 4): v_u_20, (ref 5): v_u_29 ]]
        v_u_16.AudioModFilterComponent:reset_filter_state(v_u_19)
        v_u_28:update_toggle_state()
        v_u_16.FilterColorComponent:reset_filter_state(v_u_20)
        v_u_29:update_state()
    end;
    local v_u_44 = 0
    v_u_24.get_max_difficulty = function(_) --[[ Name: get_max_difficulty ]] --[[ Line: 177 ]]
        --[[ Upvalues: (ref 1): v_u_44 ]]
        return v_u_44;
    end;
    local v_u_45 = v_u_2:new()
    v_u_24.get_songkey_set = function(_) --[[ Name: get_songkey_set ]] --[[ Line: 179 ]]
        --[[ Upvalues: (copy 1): v_u_45 ]]
        return v_u_45;
    end;
    v_u_24.fill_recommended_list = function(_, p_u_46) --[[ Name: fill_recommended_list ]] --[[ Line: 181 ]]
        --[[ Upvalues: (ref 1): v_u_44, (copy 2): v_u_45, (copy 3): p_u_21, (ref 4): v_u_3, (ref 5): v_u_11, (ref 6): v_u_12, (ref 7): v_u_9, (ref 8): v_u_8, (ref 9): v_u_29, (ref 10): v_u_14, (ref 11): v_u_19, (ref 12): v_u_18, (ref 13): v_u_13, (ref 14): l_SongRecommendation_0, (ref 15): l_RecommendationType_0, (ref 16): v_u_10, (ref 17): v_u_30, (ref 18): v_u_32, (ref 19): v_u_31, (copy 20): p_u_22 ]]
        v_u_44 = 0
        v_u_45:clear()
        p_u_46:clear()
        local v_u_47 = p_u_21._player_blob_manager:get_player_blob()
        local v_u_48 = p_u_21._player_blob_manager:get_server_mission_data()
        local v49 = p_u_21._player_blob_manager:get_server_leaderboard_data()
        local v50 = p_u_21._player_blob_manager:get_server_song_shop_available_items_data()
        local v_u_51 = v_u_3:new()
        v_u_11:playerblob_missiondata_available_foreach(v_u_47, v_u_48, v_u_12.Daily, function(p52) --[[ Line: 192 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_47, (copy 3): v_u_48, (ref 4): v_u_12, (ref 5): v_u_9, (copy 6): v_u_51 ]]
            if v_u_11:playerblob_missiondata_missionid_is_completeable(v_u_47, v_u_48, v_u_12.Daily, v_u_11:mission_get_id(p52)) ~= true and v_u_9:singleton():contains_key((v_u_11:mission_get_targetsong(p52))) then
                v_u_51:push_back_to(v_u_11:mission_get_difficulty(p52), p52)
            end;
        end)
        local v_u_53 = v_u_3:new()
        v_u_11:playerblob_missiondata_available_foreach(v_u_47, v_u_48, v_u_12.Weekly, function(p54) --[[ Line: 205 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_47, (copy 3): v_u_48, (ref 4): v_u_12, (ref 5): v_u_9, (copy 6): v_u_53 ]]
            if v_u_11:playerblob_missiondata_missionid_is_completeable(v_u_47, v_u_48, v_u_12.Weekly, v_u_11:mission_get_id(p54)) ~= true and v_u_9:singleton():contains_key((v_u_11:mission_get_targetsong(p54))) then
                v_u_53:push_back_to(v_u_11:mission_get_difficulty(p54), p54)
            end;
        end)
        local v55 = v_u_3:new()
        for v56 = 1, #v49 do
            local v57 = v49[v56]
            local l_SongKey_0 = v57.SongKey
            v_u_8:is_true(v_u_9:singleton():contains_key(l_SongKey_0))
            v55:push_back_to(v_u_9:singleton():key_get_audiomod(l_SongKey_0), v57)
        end;
        local v58 = v_u_11:playerblob_get_mission_difficulty(v_u_47)
        local v_u_59, v_u_60, v_u_61 = v_u_29:get_filter_colors()
        local function f_filter_playable_function(p62) --[[ Name: filter_playable_function ]] --[[ Line: 228 ]]
            --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_47, (ref 3): p_u_21 ]]
            return v_u_14:playerblob_has_access_to_song(v_u_47, p62, p_u_21._player_blob_manager:get_day_id(), p_u_21._player_blob_manager:get_cached_collection_info());
        end;
        local function f_filter_add_function(p63) --[[ Name: filter_add_function ]] --[[ Line: 232 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_9, (copy 3): v_u_59, (ref 4): v_u_29, (copy 5): v_u_60, (copy 6): v_u_61, (ref 7): v_u_18, (copy 8): f_filter_playable_function ]]
            if v_u_19:get(v_u_9:singleton():key_get_audiomod(p63)) == true then
                if v_u_59 and v_u_29:songkey_test_filter_colors(p63, v_u_60, v_u_61) ~= true then
                    return false;
                else
                    return v_u_18 ~= true and true or f_filter_playable_function(p63);
                end;
            else
                return false;
            end;
        end;
        for _, v64 in v_u_13:all_difficulty_asc_list():key_itr() do
            if v64 == v_u_13.Amateur and v_u_13.Amateur <= v58 then
                for _, v65 in v55:list_of(v_u_9.MOD_NORMAL):key_itr() do
                    local l_SongKey_1 = v65.SongKey
                    if f_filter_add_function(l_SongKey_1) then
                        p_u_46:push_front(l_SongRecommendation_0:new(l_SongKey_1, l_RecommendationType_0.Leaderboard):set_data(v65))
                    end;
                end;
            end;
            if v64 == v_u_13.Pro and v_u_13.Pro <= v58 then
                for _, v66 in v55:list_of(v_u_9.MOD_HARDMODE):key_itr() do
                    local l_SongKey_2 = v66.SongKey
                    if f_filter_add_function(l_SongKey_2) then
                        p_u_46:push_front(l_SongRecommendation_0:new(l_SongKey_2, l_RecommendationType_0.Leaderboard):set_data(v66))
                    end;
                end;
            end;
            for _, v67 in v_u_53:list_of(v64):key_itr() do
                local v68 = v_u_11:mission_get_targetsong(v67)
                v_u_8:is_true(v_u_9:singleton():contains_key(v68))
                if f_filter_add_function(v68) then
                    p_u_46:push_front(l_SongRecommendation_0:new(v68, l_RecommendationType_0.WeeklyMission):set_data(v67))
                end;
            end;
            for _, v69 in v_u_51:list_of(v64):key_itr() do
                local v70 = v_u_11:mission_get_targetsong(v69)
                v_u_8:is_true(v_u_9:singleton():contains_key(v70))
                if f_filter_add_function(v70) then
                    p_u_46:push_front(l_SongRecommendation_0:new(v70, l_RecommendationType_0.DailyMission):set_data(v69))
                end;
            end;
        end;
        for v71 = 1, #v50 do
            local v72 = v50[v71]
            local l_SongKey_3 = v72.SongKey
            v_u_8:is_true(v_u_9:singleton():contains_key(l_SongKey_3))
            if v72.SaleComboKey == nil or v_u_10:get_count_for_song_shop_saleid(v_u_47, v72.SaleId) ~= 0 then
                if f_filter_add_function(l_SongKey_3) then
                    p_u_46:push_back(l_SongRecommendation_0:new(l_SongKey_3, l_RecommendationType_0.SongShop):set_data(v72))
                end;
            else
                p_u_46:push_front(l_SongRecommendation_0:new(l_SongKey_3, l_RecommendationType_0.SongShopSale):set_data(v72))
            end;
        end;
        local function f_filter_recently_added_not_in_list(p73) --[[ Name: filter_recently_added_not_in_list ]] --[[ Line: 299 ]]
            --[[ Upvalues: (copy 1): p_u_46 ]]
            local v74 = true
            for v75 = 1, p_u_46:count() do
                if p73 == p_u_46:get(v75):get_songkey() then
                    return false;
                end;
            end;
            return v74;
        end;
        if v58 <= v_u_13.Novice then
            if f_filter_add_function(v_u_30) then
                p_u_46:push_front(l_SongRecommendation_0:new(v_u_30, l_RecommendationType_0.EasyMode))
            end;
            if v_u_32 and (v_u_9:singleton():contains_key(v_u_31) and f_filter_add_function(v_u_31)) then
                p_u_46:push_back(l_SongRecommendation_0:new(v_u_31, l_RecommendationType_0.ArtistEvent))
            end;
        else
            if f_filter_add_function(v_u_30) then
                p_u_46:push_back(l_SongRecommendation_0:new(v_u_30, l_RecommendationType_0.EasyMode))
            end;
            if v_u_32 and (v_u_9:singleton():contains_key(v_u_31) and f_filter_add_function(v_u_31)) then
                p_u_46:push_front(l_SongRecommendation_0:new(v_u_31, l_RecommendationType_0.ArtistEvent))
            end;
        end;
        local v76 = p_u_21._player_blob_manager:get_recently_acquired_songids_list()
        for v77 = 1, v76:count() do
            if v77 > 3 then
                break;
            end;
            local v78 = v76:get(v77)
            if v_u_14:playerblob_has_access_to_song(v_u_47, v78, p_u_21._player_blob_manager:get_day_id(), p_u_21._player_blob_manager:get_cached_collection_info()) and f_filter_recently_added_not_in_list(v78) then
                p_u_46:push_front(l_SongRecommendation_0:new(v78, l_RecommendationType_0.RecentlyAcquired):set_data(v77))
            end;
        end;
        local v_u_79 = string.lower(p_u_22:get_filter_search_name())
        local v_u_80 = string.lower(p_u_22:get_filter_artist_name())
        local v_u_81 = p_u_22:get_filter_search_difficulty()
        p_u_46:remove_if(function(p82) --[[ Line: 340 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_45, (copy 3): v_u_79, (copy 4): v_u_80, (copy 5): v_u_81, (ref 6): v_u_44 ]]
            local v83 = p82:get_songkey()
            if v_u_9:singleton():contains_key(v83) then
                v_u_45:add_set(v83)
                if string.find(string.lower(v_u_9:singleton():get_title_for_key(v83)), v_u_79, 1, true) == nil then
                    return true;
                end;
                if string.find(string.lower(v_u_9:singleton():get_artist_for_key(v83)), v_u_80, 1, true) == nil then
                    return true;
                end;
                local v84 = v_u_9:singleton():get_difficulty_for_key(v83)
                if v84 < v_u_81 then
                    return true;
                end;
                v_u_44 = math.max(v_u_44, v84)
            end;
            return false;
        end)
    end;
    local v_u_85 = -1
    v_u_24.load_data = function(p86, p87) --[[ Name: load_data ]] --[[ Line: 366 ]]
        --[[ Upvalues: (copy 1): f_reroll_random_easy_mode_songkey, (ref 2): v_u_27, (ref 3): v_u_1, (ref 4): v_u_85, (copy 5): p_u_21 ]]
        f_reroll_random_easy_mode_songkey()
        v_u_27 = v_u_1:new()
        v_u_85 = p_u_21._player_blob_manager:get_global_time_float()
        local v88 = v_u_27
        p_u_21._player_blob_manager:get_player_blob()
        p86:fill_recommended_list(v88)
        p87()
    end;
    v_u_24.get_page_total = function(p89) --[[ Name: get_page_total ]] --[[ Line: 378 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        return math.ceil(p89:get_recommended_list():count() / v_u_25:count());
    end;
    v_u_24.refresh = function(p90) --[[ Name: refresh ]] --[[ Line: 382 ]]
        --[[ Upvalues: (ref 1): v_u_27, (copy 2): p_u_22, (copy 3): v_u_25 ]]
        p90:fill_recommended_list(v_u_27)
        local v91 = p_u_22:get_page()
        local v92 = p90:get_recommended_list()
        local v93 = false
        for v94 = 1, v_u_25:count() do
            local v95 = v_u_25:get(v94)
            local v96 = v91 * v_u_25:count() + v94
            if v96 <= v92:count() then
                local v97 = v92:get(v96)
                v95:set_visible(true)
                v95:display_recommendation(v97)
                if v97:get_songkey() == p_u_22:get_info_displayed_song_key() then
                    v93 = true
                end;
            else
                v95:set_visible(false)
            end;
        end;
        if v93 ~= true then
            p_u_22:hide_info_section()
        end;
    end;
    v_u_24.set_visible = function(_, p98) --[[ Name: set_visible ]] --[[ Line: 408 ]]
        --[[ Upvalues: (ref 1): v_u_85, (copy 2): v_u_25, (copy 3): v_u_26 ]]
        v_u_85 = -1
        for v99 = 1, v_u_25:count() do
            v_u_25:get(v99):set_visible(p98)
        end;
        for v100 = 1, v_u_26:count() do
            v_u_26:get(v100):set_visible(p98)
        end;
    end;
    v_u_24.layout = function(_) --[[ Name: layout ]] --[[ Line: 418 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        for v101 = 1, v_u_25:count() do
            v_u_25:get(v101):layout()
        end;
    end;
    v_u_24.behaviour_update = function(_, p102) --[[ Name: behaviour_update ]] --[[ Line: 424 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        for v103 = 1, v_u_25:count() do
            v_u_25:get(v103):behaviour_update(p102)
        end;
    end;
    v_u_24.get_play_ui = function(_) --[[ Name: get_play_ui ]] --[[ Line: 430 ]]
        --[[ Upvalues: (copy 1): p_u_22 ]]
        return p_u_22;
    end;
    f_cons()
    return v_u_24;
end;
return v17;
