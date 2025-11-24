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
local v_u_12 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.JumpChallengeLocalUtil)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
v3:require_client(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_18, (ref 5): v_u_19, (ref 6): v_u_20, (ref 7): v_u_21 ]]
    v_u_15 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
    v_u_16 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_17 = require(game.ReplicatedStorage.Shared.InputUtil)
    v_u_18 = require(game.ReplicatedStorage.Lobby.NPC.NPCDialogPrompt)
    v_u_19 = require(game.ReplicatedStorage.Local.SFXManager)
    v_u_20 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["create_npc"] = function(_, p_u_22, p_u_23) --[[ Name: create_npc ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (copy 3): v_u_13, (copy 4): v_u_5, (copy 5): v_u_11, (ref 6): v_u_16, (copy 7): v_u_12, (ref 8): v_u_18, (copy 9): v_u_10, (ref 10): v_u_19, (ref 11): v_u_20, (copy 12): v_u_2, (copy 13): v_u_1, (copy 14): v_u_14, (copy 15): v_u_6, (copy 16): v_u_7, (ref 17): v_u_21, (copy 18): v_u_4, (ref 19): v_u_17 ]]
        v_u_8:singleton():load_model_category(v_u_9:get_category_name_to_id(v_u_9.Category.LobbyDecoration):get("JumpChallengeAutumn"), v_u_9.Category.NPC, function(p_u_24) --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_5, (copy 3): p_u_22, (ref 4): v_u_11, (ref 5): v_u_16, (ref 6): v_u_12, (ref 7): v_u_18, (copy 8): p_u_23, (ref 9): v_u_10, (ref 10): v_u_19, (ref 11): v_u_20, (ref 12): v_u_2, (ref 13): v_u_1, (ref 14): v_u_14, (ref 15): v_u_6, (ref 16): v_u_7, (ref 17): v_u_21, (ref 18): v_u_4, (ref 19): v_u_17 ]]
            local l_PlatformAnchors_0 = p_u_24.PlatformAnchors
            local v25 = v_u_13:spawn_anchor_root_with_name_to_proto_obj(l_PlatformAnchors_0, (v_u_13:register_name_to_proto_obj_root(p_u_24.PlatformProto)))
            local v_u_26 = v_u_5:new()
            local v_u_27 = nil
            for _, v28 in v25:key_itr() do
                local v29 = v28:FindFirstChild("BoostCollision")
                if v29 then
                    v29.Parent = nil
                    v_u_26:push_back(v29)
                end;
            end;
            local function v_u_30() --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_13, (ref 3): p_u_22, (copy 4): v_u_26 ]]
                v_u_27 = v_u_13:register_boost_jump_on_collision_obj_list(p_u_22, 100, v_u_26)
            end;
            local v_u_31 = v_u_11:new()
            for _, v32 in pairs(p_u_24.CollectStars:GetChildren()) do
                v32.Parent = nil
                local v33 = tonumber(v32.Name)
                if v33 ~= nil then
                    v_u_31:add(v33, v32.PrimaryPart.CFrame)
                end;
            end;
            local v_u_34 = v_u_11:new()
            for v35, _ in v_u_31:key_itr() do
                v_u_34:add(v35, false)
            end;
            local function _() --[[ Name: get_collected_count ]] --[[ Line: 84 ]]
                --[[ Upvalues: (copy 1): v_u_34 ]]
                local v36 = 0
                for _, v37 in v_u_34:key_itr() do
                    if v37 == true then
                        v36 = v36 + 1
                    end;
                end;
                return v36;
            end;
            local v_u_38 = v_u_11:new()
            local v_u_39 = nil
            local v_u_40 = 0
            local v_u_41 = false
            local function _(p42) --[[ Name: set_spawned_platform_enabled ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_39, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_16, (ref 4): v_u_27, (ref 5): v_u_30 ]]
                if v_u_39 == p42 then
                    return;
                else
                    v_u_39 = p42
                    if p42 then
                        l_PlatformAnchors_0.Parent = v_u_16:get_lobby_environment_no_popper()
                        if v_u_27 == nil then
                            v_u_30()
                        end;
                        v_u_27:set_enabled(true)
                    else
                        l_PlatformAnchors_0.Parent = nil
                        if v_u_27 then
                            v_u_27:set_enabled(false)
                        end;
                    end;
                end;
            end;
            if v_u_39 ~= false then
                v_u_39 = false
                l_PlatformAnchors_0.Parent = nil
                if v_u_27 then
                    v_u_27:set_enabled(false)
                end;
            end;
            local l_LobbyNPCManager_0 = v_u_12.Test.LobbyNPCManager
            local v_u_43 = nil
            v_u_43 = v_u_18:new(p_u_22, p_u_23, "NPC_AutumnJumpPuzzle", "Autumn Adventure", "Collect the Leaves!", v_u_10:singleton():get_dance_assetid_for_id(5), function() --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_19, (ref 3): v_u_39, (copy 4): v_u_31, (ref 5): v_u_18, (ref 6): p_u_23, (copy 7): v_u_34, (ref 8): v_u_20, (ref 9): v_u_2, (ref 10): v_u_12, (copy 11): l_LobbyNPCManager_0, (ref 12): v_u_1, (copy 13): v_u_38, (copy 14): l_PlatformAnchors_0, (ref 15): v_u_16, (ref 16): v_u_27, (ref 17): v_u_30, (ref 18): v_u_43, (ref 19): v_u_14, (ref 20): v_u_6, (ref 21): v_u_7, (ref 22): v_u_21, (ref 23): v_u_41 ]]
                p_u_22._sfx_manager:play_sfx(v_u_19.SFX_MENU_OPEN)
                if v_u_39 ~= true then
                    for v_u_44, v_u_45 in v_u_31:key_itr() do
                        local v_u_46 = nil
                        local v_u_47 = nil
                        local v48 = v_u_18
                        local v49 = p_u_22
                        local v50 = p_u_23
                        local v51 = string.format("Autumn Leaf #%d", v_u_44)
                        local function v58() --[[ Line: 141 ]]
                            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_19, (ref 3): v_u_34, (copy 4): v_u_44, (ref 5): v_u_46, (ref 6): v_u_20 ]]
                            p_u_22._sfx_manager:play_sfx(v_u_19.SFX_ACQUIRE)
                            v_u_34:add(v_u_44, true)
                            p_u_22._npcs:remove_npc(v_u_46)
                            local l__menus_0 = p_u_22._menus
                            local v52 = v_u_20:new(p_u_22, p_u_22._spui, p_u_22._menus)
                            local l_format_0 = string.format
                            local v53 = v_u_44
                            local v54 = 0
                            local v55 = "Found!"
                            local v56 = "You found Autumn Leaf #%d!\nYou\'ve found %d total Leaf(s)."
                            for _, v57 in v_u_34:key_itr() do
                                if v57 == true then
                                    v54 = v54 + 1
                                end;
                            end;
                            l__menus_0:push_menu(v52:set_text(v55, l_format_0(v56, v53, v54)))
                        end;
                        local v59 = {
                            ["NametagPositionOffset"] = Vector3.new(0, 2.5, 0)
                        }
                        v59.FnOnLoaded = function(_, p60, _) --[[ Name: FnOnLoaded ]] --[[ Line: 152 ]]
                            --[[ Upvalues: (copy 1): v_u_45, (ref 2): v_u_47 ]]
                            p60:SetPrimaryPartCFrame(v_u_45)
                            v_u_47 = p60:FindFirstChild("ImagePart")
                        end;
                        v59.FnPostLoaded = function(p61, _, _) --[[ Name: FnPostLoaded ]] --[[ Line: 156 ]]
                            --[[ Upvalues: (ref 1): v_u_2 ]]
                            local v62 = p61:get_dialogue_trigger_popup()
                            if v62 == nil then
                                v_u_2:warnf("NPC_AutumnJumpPuzzle FnPostLoaded popup is nil")
                            else
                                v62:set_dist_max(10)
                            end;
                            local v63 = p61:get_nametag()
                            if v63 == nil then
                                v_u_2:warnf("NPC_AutumnJumpPuzzle FnPostLoaded nametag is nil")
                            else
                                v63:set_dist_max(30)
                            end;
                        end;
                        v59.FnOnUpdate = function(_, _) --[[ Name: FnOnUpdate ]] --[[ Line: 171 ]]
                            --[[ Upvalues: (ref 1): v_u_12, (ref 2): l_LobbyNPCManager_0, (ref 3): v_u_47, (ref 4): v_u_1, (ref 5): p_u_23 ]]
                            if v_u_12:singleton():should_run(l_LobbyNPCManager_0) ~= false then
                                if v_u_47 then
                                    v_u_47.CFrame = v_u_1:lookat_camera_cframe(v_u_47.Position, p_u_23._spui)
                                end;
                            end;
                        end;
                        v_u_46 = v48:new(v49, v50, "NPC_AutumnJumpPuzzle_CollectLeaf", v51, "Collect Me!", nil, v58, v59)
                        v_u_38:add(v_u_44, v_u_46)
                        p_u_22._npcs:add_npc(v_u_46)
                    end;
                    if v_u_39 ~= true then
                        v_u_39 = true
                        l_PlatformAnchors_0.Parent = v_u_16:get_lobby_environment_no_popper()
                        if v_u_27 == nil then
                            v_u_30()
                        end;
                        v_u_27:set_enabled(true)
                    end;
                    if v_u_43:get_root() ~= nil then
                        local v64 = v_u_43:get_root():FindFirstChild("Highlight")
                        if v64 ~= nil then
                            v64.Parent = nil
                        end;
                    end;
                end;
                local function f_show_npc_message() --[[ Name: show_npc_message ]] --[[ Line: 194 ]]
                    --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_14, (ref 3): v_u_43 ]]
                    local v65 = 0
                    for _, v66 in v_u_34:key_itr() do
                        if v66 == true then
                            v65 = v65 + 1
                        end;
                    end;
                    if v65 < v_u_14:get_autumn_claim_reward1_count() then
                        v_u_43:display_msg(string.format("Up for an autumn adventure? There are a bunch of special leaves scattered in these hills. Come back when you\'ve found at least %d!", v_u_14:get_autumn_claim_reward1_count()))
                        return;
                    elseif v65 < v_u_14:get_autumn_claim_reward2_count() then
                        v_u_43:display_msg(string.format("You\'ve found some leaves, but there are still more out there. Come back when you\'ve found at least %d!", v_u_14:get_autumn_claim_reward2_count()))
                        return;
                    elseif v65 < v_u_14:get_autumn_claim_reward3_count() then
                        v_u_43:display_msg(string.format("A few more leaves remain hidden out there. Come back when you\'ve found all %d!", v_u_14:get_autumn_claim_reward3_count()))
                    else
                        v_u_43:display_msg(string.format("You found all %d leaves - You can now call yourself... an \'Adept of this Autumnal Abode\'. Happy Autumn!", v_u_14:get_autumn_claim_reward3_count()))
                    end;
                end;
                f_show_npc_message()
                local l__menus_1 = p_u_22._menus
                local l__spui_0 = p_u_22._spui
                local v_u_67 = l__menus_1:push_menu(v_u_20:new(p_u_22, l__spui_0, l__menus_1):set_text("Loading...", ""):set_close_button_visible(false))
                p_u_22._evt:wait_on_event_once(v_u_6.EVT_AutumnJumpChallenge_ServerClaimReward, function(p68, p69, p70) --[[ Line: 211 ]]
                    --[[ Upvalues: (copy 1): f_show_npc_message, (copy 2): l__menus_1, (copy 3): v_u_67, (ref 4): v_u_20, (ref 5): p_u_22, (copy 6): l__spui_0, (ref 7): v_u_7, (ref 8): v_u_21 ]]
                    if p68 == true then
                        local v_u_71 = v_u_7.RewardInfo:table_to_list(p70)
                        if v_u_71:count() == 0 then
                            f_show_npc_message()
                            l__menus_1:remove_menu(v_u_67)
                        else
                            p_u_22._player_blob_manager:do_sync(function() --[[ Line: 226 ]]
                                --[[ Upvalues: (ref 1): l__menus_1, (ref 2): v_u_67, (ref 3): v_u_21, (ref 4): p_u_22, (ref 5): l__spui_0, (copy 6): v_u_71, (ref 7): f_show_npc_message ]]
                                l__menus_1:remove_menu(v_u_67)
                                l__menus_1:push_menu(v_u_21:new(p_u_22, l__spui_0, l__menus_1, v_u_71, function() --[[ Line: 229 ]]
                                    --[[ Upvalues: (ref 1): f_show_npc_message ]]
                                    f_show_npc_message()
                                end):set_header_text("Rewards"))
                            end)
                        end;
                    else
                        f_show_npc_message()
                        l__menus_1:remove_menu(v_u_67)
                        l__menus_1:push_menu(v_u_20:new(p_u_22, l__spui_0, l__menus_1):set_text("Failed", p69))
                        return;
                    end;
                end)
                local l__evt_0 = p_u_22._evt
                local l_EVT_AutumnJumpChallenge_ClientClaimReward_0 = v_u_6.EVT_AutumnJumpChallenge_ClientClaimReward
                local v72 = 0
                for _, v73 in v_u_34:key_itr() do
                    if v73 == true then
                        v72 = v72 + 1
                    end;
                end;
                l__evt_0:fire_event_to_server(l_EVT_AutumnJumpChallenge_ClientClaimReward_0, v72)
                local v74 = 0
                for _, v75 in v_u_34:key_itr() do
                    if v75 == true then
                        v74 = v74 + 1
                    end;
                end;
                if v74 >= v_u_14:get_autumn_claim_reward3_count() then
                    v_u_41 = true
                end;
            end)
            p_u_22._npcs:add_npc(v_u_43)
            p_u_22:register_lobby_update_fn(function(p76, p77) --[[ Line: 247 ]]
                --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_41, (ref 3): v_u_40, (ref 4): v_u_4, (ref 5): v_u_1, (ref 6): v_u_17, (ref 7): v_u_2 ]]
                if v_u_39 == true and v_u_41 ~= true then
                    v_u_40 = v_u_40 + v_u_4:TimescaleToDeltaTime(p76)
                end;
                if v_u_1:is_dev_build() and p77._input:control_just_released(v_u_17.KEY_DEBUG_1) then
                    p77._control_script:set_next_jump_as_boosted(true, 250)
                    p77._control_script:force_jump()
                    v_u_2:warnf("DEBUG boost jump and spawn_platform")
                end;
            end)
            p_u_22:register_lobby_exit_fn(function(_) --[[ Line: 262 ]]
                --[[ Upvalues: (ref 1): v_u_39, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_27, (copy 4): p_u_24 ]]
                if v_u_39 ~= false then
                    v_u_39 = false
                    l_PlatformAnchors_0.Parent = nil
                    if v_u_27 then
                        v_u_27:set_enabled(false)
                    end;
                end;
                l_PlatformAnchors_0:Destroy()
                p_u_24:Destroy()
            end)
            p_u_24.Parent = v_u_16:get_lobby_environment()
        end)
    end
};
