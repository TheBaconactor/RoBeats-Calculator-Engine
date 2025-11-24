-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.Override)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_9 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.JumpChallengeLocalUtil)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
v3:require_client(function() --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_17, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_20 ]]
    v_u_14 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
    v_u_15 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_16 = require(game.ReplicatedStorage.Shared.InputUtil)
    v_u_17 = require(game.ReplicatedStorage.Lobby.NPC.NPCDialogPrompt)
    v_u_18 = require(game.ReplicatedStorage.Local.SFXManager)
    v_u_19 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["create_npc"] = function(_, p_u_21, p_u_22) --[[ Name: create_npc ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (copy 3): v_u_12, (copy 4): v_u_5, (copy 5): v_u_11, (ref 6): v_u_15, (ref 7): v_u_17, (copy 8): v_u_10, (ref 9): v_u_18, (ref 10): v_u_19, (copy 11): v_u_2, (copy 12): v_u_13, (copy 13): v_u_6, (copy 14): v_u_7, (ref 15): v_u_20, (copy 16): v_u_4, (copy 17): v_u_1, (ref 18): v_u_16 ]]
        v_u_8:singleton():load_model_category(v_u_9:get_category_name_to_id(v_u_9.Category.LobbyDecoration):get("JumpChallengeCarnival"), v_u_9.Category.NPC, function(p_u_23) --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_5, (copy 3): p_u_21, (ref 4): v_u_11, (ref 5): v_u_15, (ref 6): v_u_17, (copy 7): p_u_22, (ref 8): v_u_10, (ref 9): v_u_18, (ref 10): v_u_19, (ref 11): v_u_2, (ref 12): v_u_13, (ref 13): v_u_6, (ref 14): v_u_7, (ref 15): v_u_20, (ref 16): v_u_4, (ref 17): v_u_1, (ref 18): v_u_16 ]]
            local l_PlatformAnchors_0 = p_u_23.PlatformAnchors
            local v24 = v_u_12:spawn_anchor_root_with_name_to_proto_obj(l_PlatformAnchors_0, v_u_12:register_name_to_proto_obj_root(p_u_23.PlatformProto))
            local v_u_25 = v_u_5:new()
            local v_u_26 = nil
            for _, v27 in v24:key_itr() do
                local v28 = v27:FindFirstChild("BoostCollision")
                if v28 then
                    v28.Parent = nil
                    v_u_25:push_back(v28)
                end;
            end;
            local function v_u_29() --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_12, (ref 3): p_u_21, (copy 4): v_u_25 ]]
                v_u_26 = v_u_12:register_boost_jump_on_collision_obj_list(p_u_21, 75, v_u_25)
            end;
            local v_u_30 = v_u_11:new()
            for _, v31 in pairs(p_u_23.CollectStars:GetChildren()) do
                v31.Parent = nil
                local v32 = tonumber(v31.Name)
                if v32 ~= nil then
                    v_u_30:add(v32, v31.PrimaryPart.CFrame)
                end;
            end;
            local v_u_33 = v_u_11:new()
            for v34, _ in v_u_30:key_itr() do
                v_u_33:add(v34, false)
            end;
            local function _() --[[ Name: get_collected_count ]] --[[ Line: 81 ]]
                --[[ Upvalues: (copy 1): v_u_33 ]]
                local v35 = 0
                for _, v36 in v_u_33:key_itr() do
                    if v36 == true then
                        v35 = v35 + 1
                    end;
                end;
                return v35;
            end;
            local v_u_37 = v_u_11:new()
            local v_u_38 = nil
            local v_u_39 = 0
            local v_u_40 = false
            local function _(p41) --[[ Name: set_spawned_platform_enabled ]] --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): v_u_38, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_15, (ref 4): v_u_26, (ref 5): v_u_29 ]]
                if v_u_38 == p41 then
                    return;
                else
                    v_u_38 = p41
                    if p41 then
                        l_PlatformAnchors_0.Parent = v_u_15:get_lobby_environment_no_popper()
                        if v_u_26 == nil then
                            v_u_29()
                        end;
                        v_u_26:set_enabled(true)
                    else
                        l_PlatformAnchors_0.Parent = nil
                        if v_u_26 then
                            v_u_26:set_enabled(false)
                        end;
                    end;
                end;
            end;
            local v_u_42
            if v_u_38 == false then
                v_u_42 = v_u_38
            else
                v_u_38 = false
                l_PlatformAnchors_0.Parent = nil
                if v_u_26 then
                    v_u_26:set_enabled(false)
                    v_u_42 = v_u_38
                else
                    v_u_42 = v_u_38
                end;
            end;
            local v_u_43 = nil
            v_u_43 = v_u_17:new(p_u_21, p_u_22, "NPC_CarnivalJumpPuzzle", "Collect the Hats", "Challenge Start!", v_u_10:singleton():get_dance_assetid_for_id(5), function() --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_18, (ref 3): v_u_42, (copy 4): v_u_30, (ref 5): v_u_17, (ref 6): p_u_22, (copy 7): v_u_33, (ref 8): v_u_19, (ref 9): v_u_2, (copy 10): v_u_37, (copy 11): l_PlatformAnchors_0, (ref 12): v_u_15, (ref 13): v_u_26, (ref 14): v_u_29, (ref 15): v_u_43, (ref 16): v_u_13, (ref 17): v_u_39, (ref 18): v_u_6, (ref 19): v_u_7, (ref 20): v_u_20, (ref 21): v_u_40 ]]
                p_u_21._sfx_manager:play_sfx(v_u_18.SFX_MENU_OPEN)
                if v_u_42 ~= true then
                    for v_u_44, v_u_45 in v_u_30:key_itr() do
                        local v_u_46 = nil
                        local v47 = v_u_17
                        local v48 = p_u_21
                        local v49 = p_u_22
                        local v50 = string.format("Hat #%d", v_u_44)
                        local function v57() --[[ Line: 136 ]]
                            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_18, (ref 3): v_u_33, (copy 4): v_u_44, (ref 5): v_u_46, (ref 6): v_u_19 ]]
                            p_u_21._sfx_manager:play_sfx(v_u_18.SFX_ACQUIRE)
                            v_u_33:add(v_u_44, true)
                            p_u_21._npcs:remove_npc(v_u_46)
                            local l__menus_0 = p_u_21._menus
                            local v51 = v_u_19:new(p_u_21, p_u_21._spui, p_u_21._menus)
                            local l_format_0 = string.format
                            local v52 = v_u_44
                            local v53 = 0
                            local v54 = "Found!"
                            local v55 = "You found Hat #%d!\nYou\'ve found %d total Hat(s)."
                            for _, v56 in v_u_33:key_itr() do
                                if v56 == true then
                                    v53 = v53 + 1
                                end;
                            end;
                            l__menus_0:push_menu(v51:set_text(v54, l_format_0(v55, v52, v53)))
                        end;
                        local v58 = {
                            ["NametagPositionOffset"] = Vector3.new(0, 2.5, 0)
                        }
                        v58.FnOnLoaded = function(_, p59, _) --[[ Name: FnOnLoaded ]] --[[ Line: 147 ]]
                            --[[ Upvalues: (copy 1): v_u_45 ]]
                            p59:SetPrimaryPartCFrame(v_u_45)
                        end;
                        v58.FnPostLoaded = function(p60, _, _) --[[ Name: FnPostLoaded ]] --[[ Line: 150 ]]
                            --[[ Upvalues: (ref 1): v_u_2 ]]
                            local v61 = p60:get_dialogue_trigger_popup()
                            if v61 == nil then
                                v_u_2:warnf("NPC_CarnivalJumpPuzzle FnPostLoaded popup is nil")
                            else
                                v61:set_dist_max(10)
                            end;
                            local v62 = p60:get_nametag()
                            if v62 == nil then
                                v_u_2:warnf("NPC_CarnivalJumpPuzzle FnPostLoaded nametag is nil")
                            else
                                v62:set_dist_max(30)
                            end;
                        end;
                        v_u_46 = v47:new(v48, v49, "NPC_CarnivalJumpPuzzle_CollectStar", v50, "Collect Me!", nil, v57, v58)
                        v_u_37:add(v_u_44, v_u_46)
                        p_u_21._npcs:add_npc(v_u_46)
                    end;
                    if v_u_42 ~= true then
                        v_u_42 = true
                        l_PlatformAnchors_0.Parent = v_u_15:get_lobby_environment_no_popper()
                        if v_u_26 == nil then
                            v_u_29()
                        end;
                        v_u_26:set_enabled(true)
                    end;
                    if v_u_43:get_root() ~= nil then
                        local v63 = v_u_43:get_root():FindFirstChild("Highlight")
                        if v63 ~= nil then
                            v63.Parent = nil
                        end;
                    end;
                end;
                local function f_show_npc_message() --[[ Name: show_npc_message ]] --[[ Line: 180 ]]
                    --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_13, (ref 3): v_u_43, (ref 4): v_u_39 ]]
                    local v64 = 0
                    for _, v65 in v_u_33:key_itr() do
                        if v65 == true then
                            v64 = v64 + 1
                        end;
                    end;
                    if v64 < v_u_13:get_carnival_reward_count() then
                        v_u_43:display_msg(string.format("There are %d hidden hats at this carnival. Hop on a balloon and come back when you\'ve found them all!", v_u_13:get_carnival_reward_count()))
                    else
                        v_u_43:display_msg(string.format("You found all %d hats! Hope you weren\'t afraid of heights... Time: %.1f seconds.", v_u_13:get_carnival_reward_count(), v_u_39))
                    end;
                end;
                local l__menus_1 = p_u_21._menus
                local l__spui_0 = p_u_21._spui
                local v_u_66 = l__menus_1:push_menu(v_u_19:new(p_u_21, l__spui_0, l__menus_1):set_text("Loading...", ""):set_close_button_visible(false))
                p_u_21._evt:wait_on_event_once(v_u_6.EVT_CarnivalJumpChallenge_ServerClaimReward, function(p67, p68, p69) --[[ Line: 192 ]]
                    --[[ Upvalues: (copy 1): f_show_npc_message, (copy 2): l__menus_1, (copy 3): v_u_66, (ref 4): v_u_19, (ref 5): p_u_21, (copy 6): l__spui_0, (ref 7): v_u_7, (ref 8): v_u_20 ]]
                    if p67 == true then
                        local v_u_70 = v_u_7.RewardInfo:table_to_list(p69)
                        if v_u_70:count() == 0 then
                            f_show_npc_message()
                            l__menus_1:remove_menu(v_u_66)
                        else
                            p_u_21._player_blob_manager:do_sync(function() --[[ Line: 206 ]]
                                --[[ Upvalues: (ref 1): l__menus_1, (ref 2): v_u_66, (ref 3): v_u_20, (ref 4): p_u_21, (ref 5): l__spui_0, (copy 6): v_u_70, (ref 7): f_show_npc_message ]]
                                l__menus_1:remove_menu(v_u_66)
                                l__menus_1:push_menu(v_u_20:new(p_u_21, l__spui_0, l__menus_1, v_u_70, function() --[[ Line: 209 ]]
                                    --[[ Upvalues: (ref 1): f_show_npc_message ]]
                                    f_show_npc_message()
                                end):set_header_text("Rewards"))
                            end)
                        end;
                    else
                        f_show_npc_message()
                        l__menus_1:remove_menu(v_u_66)
                        l__menus_1:push_menu(v_u_19:new(p_u_21, l__spui_0, l__menus_1):set_text("Failed", p68))
                        return;
                    end;
                end)
                local l__evt_0 = p_u_21._evt
                local l_EVT_CarnivalJumpChallenge_ClientClaimReward_0 = v_u_6.EVT_CarnivalJumpChallenge_ClientClaimReward
                local v71 = 0
                for _, v72 in v_u_33:key_itr() do
                    if v72 == true then
                        v71 = v71 + 1
                    end;
                end;
                l__evt_0:fire_event_to_server(l_EVT_CarnivalJumpChallenge_ClientClaimReward_0, v71)
                local v73 = 0
                for _, v74 in v_u_33:key_itr() do
                    if v74 == true then
                        v73 = v73 + 1
                    end;
                end;
                if v73 >= v_u_13:get_carnival_reward_count() then
                    v_u_40 = true
                end;
            end)
            p_u_21._npcs:add_npc(v_u_43)
            p_u_21:register_lobby_update_fn(function(p75, p76) --[[ Line: 226 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_40, (ref 3): v_u_39, (ref 4): v_u_4, (ref 5): v_u_1, (ref 6): v_u_16, (ref 7): v_u_2 ]]
                if v_u_42 == true and v_u_40 ~= true then
                    v_u_39 = v_u_39 + v_u_4:TimescaleToDeltaTime(p75)
                end;
                if v_u_1:is_dev_build() and p76._input:control_just_released(v_u_16.KEY_DEBUG_1) then
                    p76._control_script:set_next_jump_as_boosted(true, 250)
                    p76._control_script:force_jump()
                    v_u_2:warnf("DEBUG boost jump and spawn_platform")
                end;
            end)
            p_u_21:register_lobby_exit_fn(function(_) --[[ Line: 241 ]]
                --[[ Upvalues: (ref 1): v_u_42, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_26, (copy 4): p_u_23 ]]
                if v_u_42 ~= false then
                    v_u_42 = false
                    l_PlatformAnchors_0.Parent = nil
                    if v_u_26 then
                        v_u_26:set_enabled(false)
                    end;
                end;
                l_PlatformAnchors_0:Destroy()
                p_u_23:Destroy()
            end)
            p_u_23.Parent = v_u_15:get_lobby_environment()
        end)
    end
};
