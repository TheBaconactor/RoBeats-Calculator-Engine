-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITab)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_9 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_Shared)
local l_RecommendationType_0 = v_u_9.RecommendationType
local l_SongRecommendation_0 = v_u_9.SongRecommendation
local l_ListElement_0 = v_u_9.ListElement
local v10 = {}
local v_u_11 = true
local v_u_12 = true
local v_u_13 = v_u_9.AudioModFilterComponent:create_filter_state()
v10.new = function(_, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 29 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): l_ListElement_0, (copy 5): v_u_5, (copy 6): v_u_6, (ref 7): v_u_11, (ref 8): v_u_12, (copy 9): v_u_9, (copy 10): v_u_13, (copy 11): v_u_2, (copy 12): v_u_7, (copy 13): l_SongRecommendation_0, (copy 14): l_RecommendationType_0, (copy 15): v_u_8 ]]
    local v_u_17 = v_u_3.ControllerBase:new()
    local v_u_18 = v_u_1:new()
    local v_u_19 = v_u_1:new()
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_1, (ref 3): v_u_4, (copy 4): p_u_15, (ref 5): l_ListElement_0, (copy 6): p_u_14, (copy 7): v_u_17, (ref 8): v_u_5, (ref 9): v_u_6, (copy 10): v_u_18, (copy 11): v_u_19, (ref 12): v_u_21, (ref 13): v_u_11, (ref 14): v_u_20, (ref 15): v_u_12, (ref 16): v_u_22, (ref 17): v_u_9, (ref 18): v_u_13 ]]
        local l_NowPlayingTabItems_0 = p_u_16.NowPlayingTabItems
        local l_Proto_0 = l_NowPlayingTabItems_0.Proto
        l_Proto_0.MainSurface.SurfaceGui.Enabled = true
        l_Proto_0.SelectButton.SurfaceGui.Enabled = true
        l_Proto_0.SongImageButton.SurfaceGui.Enabled = true
        l_Proto_0.Parent = nil
        for _, v23 in v_u_1:new():push_back_table_list({
            l_NowPlayingTabItems_0.Anchor1,
            l_NowPlayingTabItems_0.Anchor2,
            l_NowPlayingTabItems_0.Anchor3,
            l_NowPlayingTabItems_0.Anchor4
        }):key_itr() do
            v23.Parent = nil
            local v24 = l_Proto_0:Clone()
            v24.Parent = l_NowPlayingTabItems_0
            v24:SetPrimaryPartCFrame(v23.CFrame)
            local v25 = v_u_4:new(p_u_15, p_u_16.PrimaryPart, v24.PrimaryPart):set_default_sgui()
            local v_u_26 = nil
            v_u_26 = l_ListElement_0:new(p_u_14, v_u_17, v24, v25, p_u_15:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v25, v24.PrimaryPart, v24.SelectButton), p_u_14._spui, function() --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_6, (ref 3): v_u_26 ]]
                p_u_14._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                v_u_26:on_select_button_pressed()
            end)):set_auto_zoffset_behaviour(true), p_u_15:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v25, v24.PrimaryPart, v24.SongImageButton), p_u_14._spui, function() --[[ Line: 80 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_6, (ref 3): v_u_26 ]]
                p_u_14._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                v_u_26:on_song_button_pressed()
            end)):set_auto_zoffset_behaviour(true))
            v_u_18:push_back(v_u_26)
            v_u_26:set_visible(false)
        end;
        local function f_create_button_toggle(p27, p_u_28) --[[ Name: create_button_toggle ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): l_NowPlayingTabItems_0, (ref 2): p_u_15, (ref 3): p_u_14, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): p_u_16, (ref 7): v_u_6, (ref 8): v_u_17, (ref 9): v_u_19 ]]
            local v29 = p27:Clone()
            v29.Parent = l_NowPlayingTabItems_0
            local v30 = p_u_15:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(p_u_15, p_u_16.PrimaryPart, v29), p_u_14._spui, function() --[[ Line: 97 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_6, (copy 3): p_u_28, (ref 4): v_u_17, (ref 5): p_u_15 ]]
                p_u_14._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_28()
                v_u_17:update_filter_buttons()
                p_u_15:reset_page()
                p_u_15:load_current_tab()
            end))
            local v31 = v_u_5:button_bind_anim_toggle(v30, function() --[[ Line: 105 ]]
                --[[ Upvalues: (ref 1): p_u_15 ]]
                return p_u_15:get_alpha();
            end)
            v_u_19:push_back(v30)
            return v31;
        end;
        v_u_21 = f_create_button_toggle(p_u_16.FilterButtonProtos.FilterSpectatableButton, function() --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = not v_u_11
        end)
        v_u_20 = f_create_button_toggle(p_u_16.FilterButtonProtos.FilterJoinableButton, function() --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12 = not v_u_12
        end)
        v_u_17:update_filter_buttons()
        v_u_22 = v_u_9.AudioModFilterComponent:create_audiomod_filter_buttons(p_u_14, p_u_15, p_u_16.PrimaryPart, v_u_13, l_NowPlayingTabItems_0, p_u_16.FilterButtonProtos.EasyModeButton, p_u_16.FilterButtonProtos.NormalModeButton, p_u_16.FilterButtonProtos.HardModeButton, function(p32) --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            v_u_19:push_back(p32)
        end, function() end)
    end;
    v_u_17.on_clear_filter = function(_) --[[ Name: on_clear_filter ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_13, (ref 3): v_u_22 ]]
        v_u_9.AudioModFilterComponent:reset_filter_state(v_u_13)
        v_u_22:update_toggle_state()
    end;
    v_u_17.update_filter_buttons = function(_) --[[ Name: update_filter_buttons ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_11, (ref 3): v_u_20, (ref 4): v_u_12 ]]
        v_u_21:set_toggle(v_u_11)
        v_u_20:set_toggle(v_u_12)
    end;
    local function _(p_u_33) --[[ Name: load_server_infos ]] --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): p_u_14 ]]
        p_u_14._player_status_manager:set_playerlist_info_update_subscribed(true)
        p_u_14._player_status_manager:wait_on_next_playerlist_update(function() --[[ Line: 146 ]]
            --[[ Upvalues: (copy 1): p_u_33 ]]
            p_u_33()
        end)
    end;
    local v_u_34 = 0
    v_u_17.get_max_difficulty = function(_) --[[ Name: get_max_difficulty ]] --[[ Line: 152 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34;
    end;
    local v_u_35 = v_u_2:new()
    v_u_17.get_songkey_set = function(_) --[[ Name: get_songkey_set ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): v_u_35 ]]
        return v_u_35;
    end;
    local v_u_36 = -1
    v_u_17.fill_recommended_list = function(_, p37) --[[ Name: fill_recommended_list ]] --[[ Line: 157 ]]
        --[[ Upvalues: (ref 1): v_u_34, (copy 2): v_u_35, (copy 3): p_u_15, (ref 4): v_u_7, (ref 5): v_u_13, (copy 6): p_u_14, (ref 7): l_SongRecommendation_0, (ref 8): l_RecommendationType_0, (ref 9): v_u_12, (ref 10): v_u_8, (ref 11): v_u_11, (ref 12): v_u_36 ]]
        v_u_34 = 0
        v_u_35:clear()
        p37:clear()
        local v_u_38 = string.lower(p_u_15:get_filter_search_name())
        local v_u_39 = string.lower(p_u_15:get_filter_artist_name())
        local v_u_40 = p_u_15:get_filter_search_difficulty()
        local function f_songkey_do_add(p41) --[[ Name: songkey_do_add ]] --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_35, (copy 3): v_u_38, (copy 4): v_u_39, (copy 5): v_u_40, (ref 6): v_u_13, (ref 7): v_u_34 ]]
            if v_u_7:singleton():contains_key(p41) ~= true then
                return false;
            end;
            v_u_35:add_set(p41)
            if string.find(string.lower(v_u_7:singleton():get_title_for_key(p41)), v_u_38, 1, true) == nil then
                return false;
            end;
            if string.find(string.lower(v_u_7:singleton():get_artist_for_key(p41)), v_u_39, 1, true) == nil then
                return false;
            end;
            local v42 = v_u_7:singleton():get_difficulty_for_key(p41)
            if v42 < v_u_40 then
                return false;
            end;
            if v_u_13:get(v_u_7:singleton():key_get_audiomod(p41)) ~= true then
                return false;
            end;
            v_u_34 = math.max(v_u_34, v42)
            return true;
        end;
        local v43 = p_u_14._player_status_manager:get_cached_playerlist_info_list()
        local v44 = p_u_14._dance_club_manager:get_current_song_info()
        if v_u_7:singleton():contains_key(v44) and f_songkey_do_add(v44) then
            p37:push_back(l_SongRecommendation_0:new(v44, l_RecommendationType_0.DJClubSong):set_data(v44))
        end;
        if v_u_12 == true then
            for v45 = 1, v43:count() do
                local v46 = v43:get(v45)
                if v46:get_activity() == v_u_8.MatchMaking and f_songkey_do_add(v46:get_songkey()) then
                    p37:push_back(l_SongRecommendation_0:new(v46:get_songkey(), l_RecommendationType_0.JoinMatch):set_data(v46))
                end;
            end;
        end;
        if v_u_11 == true then
            for v47 = 1, v43:count() do
                local v48 = v43:get(v47)
                if v48:get_activity() == v_u_8.Match and f_songkey_do_add(v48:get_songkey()) then
                    p37:push_back(l_SongRecommendation_0:new(v48:get_songkey(), l_RecommendationType_0.SpectateMatch):set_data(v48))
                end;
            end;
        end;
        v_u_36 = p_u_14._player_status_manager:get_playerlist_updated_time()
    end;
    local v_u_49 = v_u_1:new()
    v_u_17.get_recommended_list = function(_) --[[ Name: get_recommended_list ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49;
    end;
    local v_u_50 = -1
    v_u_17.load_data = function(p_u_51, p_u_52) --[[ Name: load_data ]] --[[ Line: 248 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_1, (ref 3): v_u_50, (copy 4): p_u_14 ]]
        v_u_49 = v_u_1:new()
        v_u_50 = p_u_14._player_blob_manager:get_global_time_float()
        local v_u_53 = v_u_50
        local v_u_54 = v_u_49
        p_u_14._player_blob_manager:get_player_blob()
        local function v_u_55() --[[ Line: 259 ]]
            --[[ Upvalues: (copy 1): p_u_51, (copy 2): v_u_54, (copy 3): v_u_53, (ref 4): v_u_50, (copy 5): p_u_52 ]]
            p_u_51:fill_recommended_list(v_u_54)
            if v_u_53 == v_u_50 then
                p_u_52()
            end;
        end;
        p_u_14._player_status_manager:set_playerlist_info_update_subscribed(true)
        p_u_14._player_status_manager:wait_on_next_playerlist_update(function() --[[ Line: 146 ]]
            --[[ Upvalues: (copy 1): v_u_55 ]]
            v_u_55()
        end)
    end;
    v_u_17.get_page_total = function(p56) --[[ Name: get_page_total ]] --[[ Line: 268 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return math.ceil(p56:get_recommended_list():count() / v_u_18:count());
    end;
    v_u_17.refresh = function(p57) --[[ Name: refresh ]] --[[ Line: 272 ]]
        --[[ Upvalues: (ref 1): v_u_49, (copy 2): p_u_15, (copy 3): v_u_18 ]]
        p57:fill_recommended_list(v_u_49)
        if p_u_15:get_page() + 1 > p57:get_page_total() then
            p_u_15:set_page((math.max(p57:get_page_total() - 1, 0)))
        end;
        local v58 = p_u_15:get_page()
        local v59 = p57:get_recommended_list()
        local v60 = false
        for v61 = 1, v_u_18:count() do
            local v62 = v_u_18:get(v61)
            local v63 = v58 * v_u_18:count() + v61
            if v63 <= v59:count() then
                local v64 = v59:get(v63)
                v62:set_visible(true)
                v62:display_recommendation(v64)
                if v64:get_songkey() == p_u_15:get_info_displayed_song_key() then
                    v60 = true
                end;
            else
                v62:set_visible(false)
            end;
        end;
        if v60 ~= true then
            p_u_15:hide_info_section()
        end;
    end;
    v_u_17.set_visible = function(_, p65) --[[ Name: set_visible ]] --[[ Line: 308 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_50, (copy 3): v_u_18, (copy 4): v_u_19 ]]
        p_u_14._player_status_manager:set_playerlist_info_update_subscribed(p65)
        v_u_50 = -1
        for v66 = 1, v_u_18:count() do
            v_u_18:get(v66):set_visible(p65)
        end;
        for v67 = 1, v_u_19:count() do
            v_u_19:get(v67):set_visible(p65)
        end;
    end;
    v_u_17.layout = function(_) --[[ Name: layout ]] --[[ Line: 319 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        for v68 = 1, v_u_18:count() do
            v_u_18:get(v68):layout()
        end;
    end;
    v_u_17.behaviour_update = function(p69, p70) --[[ Name: behaviour_update ]] --[[ Line: 325 ]]
        --[[ Upvalues: (ref 1): v_u_36, (copy 2): p_u_14, (copy 3): p_u_15, (copy 4): v_u_18 ]]
        if v_u_36 ~= p_u_14._player_status_manager:get_playerlist_updated_time() then
            p69:refresh()
            p_u_15:update_page_display()
        end;
        for v71 = 1, v_u_18:count() do
            v_u_18:get(v71):behaviour_update(p70)
        end;
    end;
    v_u_17.requires_reload_on_menu_refocus = function(_) --[[ Name: requires_reload_on_menu_refocus ]] --[[ Line: 336 ]]
        return true;
    end;
    v_u_17.get_play_ui = function(_) --[[ Name: get_play_ui ]] --[[ Line: 338 ]]
        --[[ Upvalues: (copy 1): p_u_15 ]]
        return p_u_15;
    end;
    f_cons()
    return v_u_17;
end;
return v10;
