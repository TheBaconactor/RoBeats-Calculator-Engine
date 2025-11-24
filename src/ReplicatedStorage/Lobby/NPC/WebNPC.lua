-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:36 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPCPopup)
local v_u_5 = require(game.ReplicatedStorage.Lobby.NPCPopupDialogue)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_11 = require(game.ReplicatedStorage.Menu.SPUIChildUniqueSystemButton)
local v12 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
v12:require_client(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_17 ]]
    v_u_13 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_15 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.WebNPCShopUI)
end)
local v18 = {}
local v_u_19 = {
    ["TriggerPopup"] = 1,
    ["Dialogue"] = 2
}
v18.new = function(_, p_u_20, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 40 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_19, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_3, (ref 6): v_u_13, (copy 7): v_u_6, (ref 8): v_u_15, (copy 9): v_u_8, (ref 10): v_u_16, (ref 11): v_u_14, (copy 12): v_u_2, (copy 13): v_u_11, (copy 14): v_u_10, (ref 15): v_u_17, (copy 16): v_u_7, (copy 17): v_u_9 ]]
    local v_u_25 = v_u_1:new(p_u_21, p_u_22)
    local l_TriggerPopup_0 = v_u_19.TriggerPopup
    local v_u_26 = v_u_4:new(p_u_22)
    local v_u_27 = v_u_5:new(p_u_22, p_u_22._lobby_join:get_character_manager())
    local v_u_28 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): p_u_23, (copy 3): p_u_22, (copy 4): p_u_21, (ref 5): v_u_3, (ref 6): l_TriggerPopup_0, (ref 7): v_u_19, (ref 8): v_u_28, (copy 9): p_u_24, (copy 10): p_u_20, (ref 11): v_u_13, (ref 12): v_u_6, (ref 13): v_u_15, (ref 14): v_u_8, (ref 15): v_u_16, (ref 16): v_u_14, (ref 17): v_u_27, (ref 18): v_u_2, (ref 19): v_u_11, (ref 20): v_u_10, (ref 21): v_u_17, (ref 22): v_u_7, (copy 23): v_u_25 ]]
        v_u_26:create_popup_on_character(game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupWebNPC, p_u_23)
        v_u_26:set_position_offset(Vector3.new(0, 4, 0))
        v_u_26:set_trigger_callback(function() --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): p_u_21, (ref 3): v_u_3, (ref 4): l_TriggerPopup_0, (ref 5): v_u_19, (ref 6): v_u_28, (ref 7): p_u_24, (ref 8): p_u_20, (ref 9): v_u_13, (ref 10): v_u_6, (ref 11): v_u_15, (ref 12): v_u_8, (ref 13): v_u_16, (ref 14): v_u_14 ]]
            local l__menus_0 = p_u_22._menus
            local l__spui_0 = p_u_22._spui
            p_u_21._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
            local function _() --[[ Name: show_dialogue ]] --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): l_TriggerPopup_0, (ref 2): v_u_19, (ref 3): v_u_28, (ref 4): p_u_24 ]]
                l_TriggerPopup_0 = v_u_19.Dialogue
                v_u_28:display_text(p_u_24:get_message())
            end;
            if p_u_20:webnpcid_should_trigger_reward(p_u_24:get_webnpcid()) == true then
                local v_u_29 = l__menus_0:push_menu(v_u_13:new(p_u_21, l__spui_0, l__menus_0):set_text("Gifting...", "Please wait."):set_close_button_visible(false))
                p_u_22._shop_local_protocol:visit_webnpc(p_u_24:get_webnpcid(), function(p30, p31, p32) --[[ Line: 76 ]]
                    --[[ Upvalues: (ref 1): p_u_20, (ref 2): p_u_24, (ref 3): v_u_6, (copy 4): l__menus_0, (copy 5): v_u_29, (ref 6): l_TriggerPopup_0, (ref 7): v_u_19, (ref 8): v_u_28, (ref 9): v_u_15, (ref 10): p_u_21, (ref 11): v_u_8, (ref 12): v_u_16, (copy 13): l__spui_0, (ref 14): v_u_14 ]]
                    p_u_20:trigger_reward_local_cache(p_u_24:get_webnpcid())
                    if p30 == true then
                        local v_u_33 = v_u_15.RewardInfo:table_to_list(p32)
                        if v_u_33:count() > 0 then
                            p_u_21._player_blob_manager:do_sync(function() --[[ Line: 87 ]]
                                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_29, (ref 3): v_u_8, (ref 4): v_u_16, (ref 5): p_u_21, (ref 6): l__spui_0, (copy 7): v_u_33, (ref 8): l_TriggerPopup_0, (ref 9): v_u_19, (ref 10): v_u_28, (ref 11): p_u_24, (ref 12): v_u_14 ]]
                                l__menus_0:remove_menu(v_u_29)
                                if v_u_8.UseRewardDescriptionInfoAcquiredUI == true then
                                    l__menus_0:push_menu(v_u_16:new(p_u_21, l__spui_0, l__menus_0, v_u_33, function() --[[ Line: 91 ]]
                                        --[[ Upvalues: (ref 1): l_TriggerPopup_0, (ref 2): v_u_19, (ref 3): v_u_28, (ref 4): p_u_24 ]]
                                        l_TriggerPopup_0 = v_u_19.Dialogue
                                        v_u_28:display_text(p_u_24:get_message())
                                    end):set_header_text("Received Gift!"):set_sub_text(string.format("You received a gift from %s.", p_u_24:get_name())))
                                else
                                    l__menus_0:push_menu(v_u_14:new(p_u_21, l__spui_0, l__menus_0, v_u_33, function() --[[ Line: 103 ]]
                                        --[[ Upvalues: (ref 1): l_TriggerPopup_0, (ref 2): v_u_19, (ref 3): v_u_28, (ref 4): p_u_24 ]]
                                        l_TriggerPopup_0 = v_u_19.Dialogue
                                        v_u_28:display_text(p_u_24:get_message())
                                    end):set_text_display("Received Gift!", string.format("You received a gift from %s.", p_u_24:get_name())))
                                end;
                            end)
                        else
                            l__menus_0:remove_menu(v_u_29)
                            l_TriggerPopup_0 = v_u_19.Dialogue
                            v_u_28:display_text(p_u_24:get_message())
                        end;
                    else
                        v_u_6:warnf("WebNPC visit_webnpc failed(%s)", (tostring(p31)))
                        l__menus_0:remove_menu(v_u_29)
                        l_TriggerPopup_0 = v_u_19.Dialogue
                        v_u_28:display_text(p_u_24:get_message())
                        return;
                    end;
                end)
            else
                l_TriggerPopup_0 = v_u_19.Dialogue
                v_u_28:display_text(p_u_24:get_message())
            end;
        end)
        v_u_27:create_popup_on_character(game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.WebNPCDialogueBox, p_u_23, function(p_u_34) --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_8, (ref 3): v_u_27, (ref 4): p_u_24, (ref 5): v_u_11, (ref 6): p_u_22, (ref 7): v_u_10, (ref 8): p_u_21, (ref 9): v_u_3, (ref 10): v_u_17 ]]
            v_u_2:ptry(function() --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_34, (ref 3): v_u_27, (ref 4): p_u_24, (ref 5): v_u_11, (ref 6): p_u_22, (ref 7): v_u_10, (ref 8): p_u_21, (ref 9): v_u_3, (ref 10): v_u_17, (ref 11): v_u_2 ]]
                if v_u_8.NPCPopupDialogButtonsEnabled == true then
                    local v35 = v_u_27:get_unique_system_buttons()
                    local v36 = v_u_27:get_unique_system_buttons_enabled_fns()
                    local l_LikeButton_0 = p_u_34.Buttons.LikeButton
                    local l_SurfaceGui_0 = l_LikeButton_0.SurfaceGui
                    local l_LikeCountDisplay_0 = l_SurfaceGui_0.Frame.LikeCountDisplay
                    local function _() --[[ Name: update_like_count_display ]] --[[ Line: 138 ]]
                        --[[ Upvalues: (copy 1): l_LikeCountDisplay_0, (ref 2): p_u_24 ]]
                        l_LikeCountDisplay_0.Text = tostring(p_u_24:get_like_count())
                    end;
                    l_LikeCountDisplay_0.Text = tostring(p_u_24:get_like_count())
                    v35:push_back(v_u_11:new(p_u_22, v_u_10:new(v_u_27, p_u_34, l_LikeButton_0), function() --[[ Line: 149 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (ref 3): v_u_17, (ref 4): p_u_24, (ref 5): v_u_2 ]]
                        p_u_21._sfx_manager:play_sfx(v_u_3.SFX_BUTTONPRESS)
                        v_u_17:webnpc_do_like(p_u_21, p_u_24, function() --[[ Line: 151 ]]
                            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_17, (ref 3): p_u_21, (ref 4): p_u_24 ]]
                            if not v_u_2:do_disable_chat() then
                                v_u_17:show_npc_messages_menu(p_u_21, p_u_24)
                            end;
                        end)
                    end):set_fn_set_visible(function(p_u_37) --[[ Line: 160 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (copy 2): l_SurfaceGui_0, (copy 3): l_LikeCountDisplay_0, (ref 4): p_u_24 ]]
                        v_u_2:ptry(function() --[[ Line: 161 ]]
                            --[[ Upvalues: (ref 1): l_SurfaceGui_0, (copy 2): p_u_37, (ref 3): l_LikeCountDisplay_0, (ref 4): p_u_24 ]]
                            l_SurfaceGui_0.Enabled = p_u_37
                            if p_u_37 == true then
                                l_LikeCountDisplay_0.Text = tostring(p_u_24:get_like_count())
                            end;
                        end)
                    end):set_visible(false))
                    v36:push_back(function() --[[ Line: 169 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_24 ]]
                        return p_u_21._player_blob_manager:get_liked_web_npc_id_set():contains(p_u_24:get_webnpcid()) == false;
                    end)
                    if v_u_2:do_disable_chat() then
                        p_u_34.Buttons.ChatButton.Parent = nil
                    else
                        local l_ChatButton_0 = p_u_34.Buttons.ChatButton
                        local l_SurfaceGui_1 = l_ChatButton_0.SurfaceGui
                        v35:push_back(v_u_11:new(p_u_22, v_u_10:new(v_u_27, p_u_34, l_ChatButton_0), function() --[[ Line: 187 ]]
                            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (ref 3): v_u_17, (ref 4): p_u_24 ]]
                            p_u_21._sfx_manager:play_sfx(v_u_3.SFX_BUTTONPRESS)
                            v_u_17:show_npc_messages_menu(p_u_21, p_u_24)
                        end):set_fn_set_visible(function(p_u_38) --[[ Line: 192 ]]
                            --[[ Upvalues: (ref 1): v_u_2, (copy 2): l_SurfaceGui_1 ]]
                            v_u_2:ptry(function() --[[ Line: 193 ]]
                                --[[ Upvalues: (ref 1): l_SurfaceGui_1, (copy 2): p_u_38 ]]
                                l_SurfaceGui_1.Enabled = p_u_38
                            end)
                        end):set_visible(false))
                        v36:push_back(function() --[[ Line: 196 ]]
                            return true;
                        end)
                    end;
                else
                    p_u_34.Buttons.Parent = nil
                    return;
                end;
            end)
        end)
        v_u_28 = v_u_7:new(p_u_24:get_name(), v_u_27:get_obj().Part, v_u_27, {
            ["OnCreate"] = function(p39) --[[ Name: OnCreate ]] --[[ Line: 202 ]]
                p39:use_r_set_alpha_v2()
            end
        })
        v_u_25:update_mode()
    end;
    v_u_25.update_mode = function(_) --[[ Name: update_mode ]] --[[ Line: 210 ]]
        --[[ Upvalues: (ref 1): l_TriggerPopup_0, (ref 2): v_u_19, (ref 3): v_u_26, (ref 4): v_u_27 ]]
        if l_TriggerPopup_0 == v_u_19.TriggerPopup then
            v_u_26:set_enabled(true)
            v_u_27:set_enabled(false)
        else
            v_u_26:set_enabled(false)
            v_u_27:set_enabled(true)
        end;
    end;
    local v_u_40 = nil
    v_u_25.set_animation_key = function(p41, p42) --[[ Name: set_animation_key ]] --[[ Line: 221 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): p_u_23 ]]
        v_u_40 = p41:load_anim(p_u_23.Humanoid, p42)
        p41:play_anim(v_u_40)
    end;
    v_u_25.update = function(p43, p44) --[[ Name: update ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): l_TriggerPopup_0, (ref 3): v_u_19, (ref 4): v_u_26, (ref 5): v_u_27, (ref 6): v_u_28, (ref 7): v_u_9 ]]
        v_u_2:profilebegin("WebNPC:update")
        p43:update_base(p44)
        if l_TriggerPopup_0 == v_u_19.TriggerPopup then
            v_u_26:update(p44)
        else
            v_u_27:update(p44)
            v_u_28:update(p44)
            if v_u_27:should_show() == false and v_u_28:is_fading_out() == false then
                v_u_28:finish()
            end;
            if v_u_28:is_fading_out() == true then
                if v_u_28:is_hidden() == true then
                    l_TriggerPopup_0 = v_u_19.TriggerPopup
                end;
            elseif v_u_28:get_time_displayed() > v_u_9.NPC_DIALOGUE_DISPLAY_TIME_SEC then
                v_u_28:finish()
            end;
        end;
        p43:update_mode()
        v_u_2:profileend()
    end;
    v_u_25.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_26, (ref 3): v_u_27, (ref 4): p_u_23 ]]
        v_u_2:ptry(function() --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): p_u_23 ]]
            if v_u_26 ~= nil then
                v_u_26:do_remove()
                v_u_26 = nil
            end;
            if v_u_27 ~= nil then
                v_u_27:do_remove()
                v_u_27 = nil
            end;
            p_u_23:Destroy()
            p_u_23 = nil
        end)
    end;
    v_u_25.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 267 ]]
        --[[ Upvalues: (copy 1): p_u_24 ]]
        return p_u_24:get_webnpcid();
    end;
    v_u_25.get_root = function(_) --[[ Name: get_root ]] --[[ Line: 271 ]]
        --[[ Upvalues: (ref 1): p_u_23 ]]
        return p_u_23;
    end;
    v_u_25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 273 ]]
        --[[ Upvalues: (copy 1): p_u_24 ]]
        return p_u_24:get_name();
    end;
    v_u_25.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 274 ]]
        return "(NPC)";
    end;
    v_u_25.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 276 ]]
        --[[ Upvalues: (ref 1): p_u_23 ]]
        return p_u_23;
    end;
    f_cons()
    return v_u_25;
end;
return v18;
