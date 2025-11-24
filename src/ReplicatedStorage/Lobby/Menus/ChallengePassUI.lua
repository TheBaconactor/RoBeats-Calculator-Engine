-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:44 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.ChallengePassUIElement)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PurchaseUtils)
local v_u_18 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_19 = {
    ["Mode"] = {
        ["Loading"] = 0,
        ["Ready"] = 1,
        ["Kill"] = -1
    }
}
local v_u_20 = Vector2.new(437, 24)
local v_u_21 = Vector2.new(829, 50)
v_u_19.new = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_19, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_11, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_8, (copy 9): v_u_12, (copy 10): v_u_17, (copy 11): v_u_16, (copy 12): v_u_7, (copy 13): v_u_13, (copy 14): v_u_15, (copy 15): v_u_14, (copy 16): v_u_20, (copy 17): v_u_21, (copy 18): v_u_18, (copy 19): v_u_10, (copy 20): v_u_9, (copy 21): v_u_6 ]]
    local v_u_25 = v_u_3:new(p_u_23, p_u_24)
    local v_u_26 = nil
    local v_u_27 = 1
    local l_Loading_0 = v_u_19.Mode.Loading
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = v_u_2:new()
    local v_u_37 = -1
    local v_u_38 = nil
    local v_u_39 = -1
    local function f_cons() --[[ Name: cons ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_1, (ref 3): v_u_11, (copy 4): v_u_25, (ref 5): v_u_39, (copy 6): p_u_22, (ref 7): v_u_35, (ref 8): v_u_5, (ref 9): v_u_4, (copy 10): p_u_23, (ref 11): v_u_8, (ref 12): l_Loading_0, (ref 13): v_u_19, (copy 14): p_u_24, (ref 15): v_u_28, (ref 16): v_u_29, (ref 17): v_u_12, (ref 18): v_u_30, (ref 19): v_u_17, (ref 20): v_u_16, (ref 21): v_u_31, (ref 22): v_u_32, (ref 23): v_u_33, (ref 24): v_u_34, (ref 25): v_u_38, (ref 26): v_u_7, (ref 27): v_u_36, (ref 28): v_u_37 ]]
        v_u_26 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.ChallengePassUI:Clone()
        v_u_26.Name = v_u_1:gen_name(v_u_26.Name)
        v_u_26.Parent = v_u_11:get_world_ui_folder()
        v_u_25._native_size = v_u_26.PrimaryPart.Size
        v_u_25._size = v_u_25._native_size
        v_u_39 = p_u_22._player_blob_manager:get_synced_time()
        v_u_35 = v_u_26.MainSurface.SurfaceGui.Frame
        v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.BackButtonSurface), p_u_23, function() --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): l_Loading_0, (ref 4): v_u_19, (ref 5): p_u_24, (ref 6): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            l_Loading_0 = v_u_19.Mode.Kill
            p_u_24:remove_menu(v_u_25)
        end))
        v_u_28 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.InfoButton), p_u_23, function() --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_25:on_info_button_pressed()
        end))
        v_u_29 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.VIPButton), p_u_23, function() --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): p_u_24, (ref 4): v_u_12, (ref 5): p_u_23 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_24:push_menu(v_u_12:new(p_u_22, p_u_23, p_u_24))
        end))
        v_u_30 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.UnlockAllTiersButton), p_u_23, function() --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): v_u_17, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_16, (ref 7): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_17:purchase_prompt(p_u_22, p_u_23, p_u_24, v_u_16.ProductID_ChallengePassSeasonUnlock, function() --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25:update_challenge_elements()
            end)
        end))
        v_u_31 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.CompleteCurrentChallengeButton), p_u_23, function() --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): v_u_17, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_16, (ref 7): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_17:purchase_prompt(p_u_22, p_u_23, p_u_24, v_u_16.ProductID_ChallengePassComplete, function() --[[ Line: 104 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25:update_challenge_elements()
            end)
        end))
        v_u_32 = v_u_35.LoadedFrame.BarSection.BarFillYellow
        v_u_33 = v_u_35.LoadedFrame.BarSection.BarText
        v_u_34 = v_u_35.LoadedFrame.BarSection.BarCheck
        v_u_38 = v_u_35.LoadedFrame.TimeSection.Display
        v_u_25:init_challenge_element_protos()
        v_u_25:update_mode()
        p_u_22._shop_local_protocol:request_challengepass_info(function(p40, p41, p42) --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_7, (ref 3): v_u_36, (ref 4): v_u_37, (ref 5): l_Loading_0, (ref 6): v_u_19, (ref 7): v_u_25 ]]
            if v_u_35:FindFirstChild("LoadedFrame") == nil then
                return v_u_7:warnf("ChallengePassUI _root_frame.LoadedFrame not found");
            end;
            v_u_35.LoadedFrame.MonthDisplay.Text = string.format("Season %d", p41)
            v_u_36 = p40
            v_u_37 = p42
            l_Loading_0 = v_u_19.Mode.Loaded
            v_u_25:update_challenge_elements()
        end)
    end;
    local v_u_43 = v_u_2:new()
    v_u_25.update_challenge_elements = function(p44) --[[ Name: update_challenge_elements ]] --[[ Line: 131 ]]
        --[[ Upvalues: (copy 1): v_u_43, (ref 2): v_u_36 ]]
        for v45 = 1, v_u_43:count() do
            local v46 = v_u_43:get(v45)
            if v_u_36:count() < v45 then
                v46:update_with_mission(nil)
            else
                v46:update_with_mission(v_u_36:get(v45))
            end;
        end;
        p44:update_mode()
    end;
    v_u_25.init_challenge_element_protos = function(p47) --[[ Name: init_challenge_element_protos ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_2, (copy 3): v_u_43, (ref 4): v_u_13, (copy 5): p_u_22 ]]
        local l_ChallengeElementProto_0 = v_u_26.ChallengeElementProto
        l_ChallengeElementProto_0.Parent = nil
        local v48 = v_u_2:new():push_back_table_list({
            v_u_26.Anchors.Anchor0,
            v_u_26.Anchors.Anchor1,
            v_u_26.Anchors.Anchor2,
            v_u_26.Anchors.Anchor3,
            v_u_26.Anchors.Anchor4,
            v_u_26.Anchors.Anchor5,
            v_u_26.Anchors.Anchor6,
            v_u_26.Anchors.Anchor7,
            v_u_26.Anchors.Anchor8,
            v_u_26.Anchors.Anchor9
        })
        for v49 = 1, v48:count() do
            v48:get(v49).Parent = nil
            v_u_43:push_back(v_u_13:new(p_u_22, p47, v_u_26, l_ChallengeElementProto_0, v48:get(v49)))
        end;
    end;
    v_u_25.update_mode = function(p50) --[[ Name: update_mode ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_19, (ref 3): v_u_28, (ref 4): v_u_29, (ref 5): v_u_30, (ref 6): v_u_31, (ref 7): v_u_35, (copy 8): v_u_43, (copy 9): p_u_22, (ref 10): v_u_15, (ref 11): v_u_14, (ref 12): v_u_36, (ref 13): v_u_33 ]]
        if l_Loading_0 == v_u_19.Mode.Loading then
            v_u_28:set_visible(false)
            v_u_29:set_visible(false)
            v_u_30:set_visible(false)
            v_u_31:set_visible(false)
            v_u_35.LoadedFrame.Visible = false
            v_u_35.LoadingFrame.Visible = true
            for v51 = 1, v_u_43:count() do
                v_u_43:get(v51):set_visible(false)
            end;
        elseif l_Loading_0 == v_u_19.Mode.Loaded then
            local v52 = p_u_22._player_blob_manager:get_player_blob()
            local v53 = v_u_15:playerblob_has_vip_for_current_day(v52, p_u_22:get_current_dayid())
            v_u_28:set_visible(true)
            v_u_29:set_visible(v53 ~= true)
            if v53 == true or v52.ChallengePassMonthActivated == true then
                v_u_30:set_visible(false)
            else
                v_u_30:set_visible(true)
            end;
            local v54 = v_u_14:playerblob_get_challengepass_active_mission(v52, v_u_36)
            if v54 == nil then
                v_u_30:set_visible(false)
                v_u_31:set_visible(false)
                v_u_35.LoadedFrame.Visible = true
                v_u_35.LoadingFrame.Visible = false
                for v55 = 1, v_u_43:count() do
                    v_u_43:get(v55):set_visible(true)
                end;
                local v56, v57 = v_u_14:playerblob_get_active_mission_point_totals(v52, v_u_36)
                p50:set_bar_num_div(v56, v57)
                v_u_33.Text = v_u_33.Text .. " (Completed)"
            else
                local v58 = v_u_14:playerblob_get_challengepass_mission_state(v52, v54, p_u_22:get_current_dayid())
                if v54 == nil or v58 ~= v_u_14.ChallengePassMissionState.Current then
                    v_u_31:set_visible(false)
                else
                    v_u_31:set_visible(true)
                end;
                v_u_35.LoadedFrame.Visible = true
                v_u_35.LoadingFrame.Visible = false
                for v59 = 1, v_u_43:count() do
                    v_u_43:get(v59):set_visible(true)
                end;
                local v60, v61 = v_u_14:playerblob_get_active_mission_point_totals(v52, v_u_36)
                p50:set_bar_num_div(v60, v61)
                if v58 == v_u_14.ChallengePassMissionState.LockedVIP then
                    v_u_33.Text = v_u_33.Text .. " (VIP Required)"
                    return;
                end;
            end;
        end;
    end;
    v_u_25.set_bar_num_div = function(_, p62, p63) --[[ Name: set_bar_num_div ]] --[[ Line: 224 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_33, (ref 3): v_u_32, (ref 4): v_u_20, (ref 5): v_u_21, (ref 6): v_u_34 ]]
        local v64 = v_u_1:clamp(p62 / p63, 0, 1)
        v_u_33.Text = string.format("%s / %s", v_u_1:comma_value(p62), v_u_1:comma_value(p63))
        v_u_32.ImageRectSize = v_u_20 * Vector2.new(v64, 1)
        v_u_32.Size = UDim2.new(0, v_u_21.X * v64, 0, v_u_21.Y)
        v_u_34.Visible = v64 >= 1
    end;
    v_u_25.claim_button_pressed = function(p_u_65) --[[ Name: claim_button_pressed ]] --[[ Line: 233 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_14, (ref 3): v_u_36, (ref 4): v_u_18, (copy 5): p_u_24, (ref 6): v_u_10, (copy 7): p_u_23, (ref 8): v_u_9, (ref 9): v_u_8 ]]
        local v66 = v_u_14:playerblob_get_challengepass_active_mission(p_u_22._player_blob_manager:get_player_blob(), v_u_36)
        local v67 = v_u_18:invalid_songkey()
        local v_u_68
        if v66 == nil then
            v_u_68 = v67
        else
            local v69 = v66:get_reward_type()
            v_u_68 = v66:get_reward_id()
            if not (v_u_14.RewardTypesSong:contains(v69) and v_u_18:singleton():contains_key(v_u_68)) then
                v_u_68 = v67
            end;
        end;
        local v_u_70 = p_u_24:push_menu(v_u_10:new(p_u_22, p_u_23, p_u_24):set_text("Claiming...", "Please wait..."):set_close_button_visible(false))
        p_u_22._evt:wait_on_event_once(v_u_9.EVT_ChallengePass_ServerClaimResponse, function(p_u_71, p_u_72) --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): p_u_24, (copy 3): v_u_70, (copy 4): p_u_65, (ref 5): v_u_8, (ref 6): v_u_68, (ref 7): v_u_18, (ref 8): v_u_10, (ref 9): p_u_23 ]]
            p_u_22._player_blob_manager:do_sync(function() --[[ Line: 247 ]]
                --[[ Upvalues: (ref 1): p_u_24, (ref 2): v_u_70, (ref 3): p_u_65, (copy 4): p_u_71, (ref 5): p_u_22, (ref 6): v_u_8, (ref 7): v_u_68, (ref 8): v_u_18, (ref 9): v_u_10, (ref 10): p_u_23, (copy 11): p_u_72 ]]
                p_u_24:remove_menu(v_u_70)
                p_u_65:update_challenge_elements()
                local v73
                if p_u_71 then
                    v73 = "Claim Success!"
                    p_u_22._sfx_manager:play_sfx(v_u_8.SFX_FANFARE)
                    if v_u_68 ~= v_u_18:invalid_songkey() then
                        p_u_22._player_blob_manager:add_recently_acquired_songid(v_u_68)
                    end;
                else
                    v73 = "Claim Failed"
                end;
                p_u_24:push_menu(v_u_10:new(p_u_22, p_u_23, p_u_24):set_text(v73, p_u_72))
            end)
        end)
        p_u_22._evt:fire_event_to_server(v_u_9.EVT_ChallengePass_ClientClaimRequest)
    end;
    v_u_25.on_info_button_pressed = function(_) --[[ Name: on_info_button_pressed ]] --[[ Line: 267 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_24, (ref 3): v_u_10, (copy 4): p_u_22, (copy 5): p_u_23 ]]
        local v74 = "Earn points by playing to unlock new reward tiers every season.\nThe following actions reward points:"
        for _, v75 in v_u_14:get_challenge_pass_action_info():key_itr() do
            v74 = v74 .. string.format("\n%s - %d point(s)", v75:get_name(), v75:get_point_reward())
        end;
        p_u_24:push_menu(v_u_10:new(p_u_22, p_u_23, p_u_24):set_text("Challenge Pass Information", v74))
    end;
    v_u_25.layout = function(p76) --[[ Name: layout ]] --[[ Line: 279 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_27, (ref 3): v_u_26, (copy 4): v_u_43 ]]
        p_u_23:uiobj_rescale_to_max_nxy(p76, 0.9, 0.9, v_u_27)
        v_u_26:SetPrimaryPartCFrame(p_u_23:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p76:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        for v77 = 1, v_u_43:count() do
            v_u_43:get(v77):layout()
        end;
    end;
    v_u_25.behaviour_update = function(p78, p79, p80) --[[ Name: behaviour_update ]] --[[ Line: 291 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_6, (ref 3): v_u_38, (ref 4): v_u_1, (copy 5): p_u_22, (ref 6): v_u_39, (copy 7): v_u_43 ]]
        p78:behaviour_update_base(p79, p80)
        v_u_37 = math.max(v_u_37 - v_u_6:TimescaleToDeltaTime(p79), 0)
        v_u_38.Text = v_u_1:format_sec_time(v_u_37)
        if p_u_22._player_blob_manager:is_synced() and p_u_22._player_blob_manager:get_synced_time() ~= v_u_39 then
            v_u_39 = p_u_22._player_blob_manager:get_synced_time()
            p78:update_challenge_elements()
        end;
        for v81 = 1, v_u_43:count() do
            v_u_43:get(v81):behaviour_update(p79)
        end;
    end;
    v_u_25.visual_update = function(p82, p83, p84) --[[ Name: visual_update ]] --[[ Line: 307 ]]
        p82:visual_update_base(p83, p84)
    end;
    v_u_25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 311 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26:Destroy()
    end;
    local v_u_85 = -1
    v_u_25.set_alpha = function(_, p86, p87) --[[ Name: set_alpha ]] --[[ Line: 316 ]]
        --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_1, (ref 3): v_u_26 ]]
        if v_u_85 ~= p86 or p87 == true then
            v_u_85 = p86
            v_u_1:r_set_alpha(v_u_26, v_u_85)
        end;
    end;
    v_u_25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 323 ]]
        --[[ Upvalues: (ref 1): v_u_85 ]]
        return v_u_85;
    end;
    v_u_25.set_scale = function(_, p88) --[[ Name: set_scale ]] --[[ Line: 324 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27 = p88
    end;
    v_u_25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 325 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v_u_25.get_native_size = function(p89) --[[ Name: get_native_size ]] --[[ Line: 326 ]]
        return p89._native_size;
    end;
    v_u_25.get_size = function(p90) --[[ Name: get_size ]] --[[ Line: 327 ]]
        return p90._size;
    end;
    v_u_25.set_size = function(p91, p92) --[[ Name: set_size ]] --[[ Line: 328 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        p91._size = p92
        v_u_26.PrimaryPart.Size = Vector3.new(p92.X, p92.Y, 0)
    end;
    v_u_25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 332 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.Position;
    end;
    v_u_25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 333 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.SurfaceGui;
    end;
    v_u_25.set_showing = function(_, p93) --[[ Name: set_showing ]] --[[ Line: 334 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_11 ]]
        if p93 then
            v_u_26.Parent = v_u_11:get_world_ui_folder()
        else
            v_u_26.Parent = nil
        end;
    end;
    f_cons()
    return v_u_25;
end;
return v_u_19;
