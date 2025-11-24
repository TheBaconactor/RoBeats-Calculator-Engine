-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
local v_u_1 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPCPopup)
local v_u_5 = require(game.ReplicatedStorage.Lobby.NPCPopupDialogue)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
require(game.ReplicatedStorage.Shared.Constants)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_10 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_11 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_12 = require(game.ReplicatedStorage.Shared.Override)
local v_u_13 = require(game.ReplicatedStorage.Shared.NoCollideGroup)
local v14 = {}
local v_u_15 = {
    ["TriggerPopup"] = 1,
    ["Dialogue"] = 2
}
v14.new = function(_, p_u_16, p_u_17, p18, p19, p20, p_u_21, p_u_22, p23) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_11, (copy 3): v_u_15, (copy 4): v_u_6, (copy 5): v_u_12, (copy 6): v_u_10, (copy 7): v_u_4, (copy 8): v_u_5, (copy 9): v_u_13, (copy 10): v_u_8, (copy 11): v_u_1, (copy 12): v_u_3, (copy 13): v_u_7, (copy 14): v_u_2 ]]
    local v_u_24 = p23 == nil and {} or p23
    local v25 = v_u_9:get_category_name_to_id(v_u_9:get_category_table_to_name():get(v_u_9.NPC)):get(p18)
    v_u_11:is_non_nil(v25)
    local l_TriggerPopup_0 = v_u_15.TriggerPopup
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local function f_define_local_fns(p30) --[[ Name: define_local_fns ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_26, (ref 3): v_u_28, (ref 4): v_u_6, (ref 5): l_TriggerPopup_0, (ref 6): v_u_15, (ref 7): v_u_27, (ref 8): v_u_12, (ref 9): v_u_24 ]]
        p30.get_environment_objects = function(_) --[[ Name: get_environment_objects ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        p30.get_dialogue_trigger_popup = function(_) --[[ Name: get_dialogue_trigger_popup ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26;
        end;
        p30.display_msg = function(_, p31) --[[ Name: display_msg ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_6, (ref 3): l_TriggerPopup_0, (ref 4): v_u_15 ]]
            if v_u_28 == nil then
                return v_u_6:warnf("NPCDialogPrompt:display_msg when _dialogue is nil");
            end;
            l_TriggerPopup_0 = v_u_15.Dialogue
            v_u_28:display_text(p31)
        end;
        p30.update_mode = function(_) --[[ Name: update_mode ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_27, (ref 3): v_u_26, (ref 4): v_u_6, (ref 5): l_TriggerPopup_0, (ref 6): v_u_15 ]]
            if v_u_28 == nil or (v_u_27 == nil or v_u_26 == nil) then
                return v_u_6:warnf("NPCDialogPrompt:update_mode when _dialogue or _dialogue_trigger_popup is nil");
            elseif l_TriggerPopup_0 == v_u_15.TriggerPopup then
                v_u_26:set_enabled(true)
                v_u_27:set_enabled(false)
            else
                v_u_26:set_enabled(false)
                v_u_27:set_enabled(true)
            end;
        end;
        local v_u_32 = v_u_12:get_base_fn(p30, "update")
        p30.update = function(p33, p34) --[[ Name: update ]] --[[ Line: 73 ]]
            --[[ Upvalues: (copy 1): v_u_32, (ref 2): v_u_28, (ref 3): v_u_27, (ref 4): v_u_26, (ref 5): l_TriggerPopup_0, (ref 6): v_u_15, (ref 7): v_u_24 ]]
            v_u_32(p33, p34)
            if v_u_28 ~= nil and (v_u_27 ~= nil and v_u_26 ~= nil) then
                if l_TriggerPopup_0 == v_u_15.TriggerPopup then
                    v_u_26:update(p34)
                else
                    v_u_27:update(p34)
                    v_u_28:update(p34)
                    if v_u_27:should_show() == false and v_u_28:is_fading_out() == false then
                        v_u_28:finish()
                    end;
                    if v_u_28:is_fading_out() == true then
                        if v_u_28:is_hidden() == true then
                            l_TriggerPopup_0 = v_u_15.TriggerPopup
                        end;
                    elseif v_u_28:get_time_displayed() > 5 then
                        v_u_28:finish()
                    end;
                end;
                p33:update_mode()
                if v_u_24.FnOnUpdate ~= nil then
                    v_u_24.FnOnUpdate(p33, p34)
                end;
            end;
        end;
        local v_u_35 = v_u_12:get_base_fn(p30, "cleanup")
        p30.cleanup = function(p36) --[[ Name: cleanup ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_29 ]]
            v_u_35(p36)
            if v_u_29 then
                for _, v37 in v_u_29:key_itr() do
                    v37:Destroy()
                end;
                v_u_29:clear()
            end;
        end;
    end;
    return v_u_10:new(p_u_16, p_u_17, v25, p19, p20, nil, true, function(p_u_38, p_u_39, p_u_40) --[[ Line: 125 ]]
        --[[ Upvalues: (copy 1): f_define_local_fns, (ref 2): v_u_24, (ref 3): v_u_26, (ref 4): v_u_4, (copy 5): p_u_17, (ref 6): v_u_27, (ref 7): v_u_5, (ref 8): v_u_13, (ref 9): v_u_29, (ref 10): v_u_8, (ref 11): v_u_1, (copy 12): p_u_21, (copy 13): p_u_16, (ref 14): v_u_3, (ref 15): l_TriggerPopup_0, (ref 16): v_u_15, (copy 17): p_u_22, (ref 18): v_u_28, (ref 19): v_u_7, (ref 20): v_u_2 ]]
        f_define_local_fns(p_u_38)
        if v_u_24.FnOnLoaded ~= nil then
            v_u_24.FnOnLoaded(p_u_38, p_u_39, p_u_40)
        end;
        if v_u_24.FnPostLoaded ~= nil then
            p_u_38:get_on_loaded_fns():push_back(function() --[[ Line: 132 ]]
                --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_38, (copy 3): p_u_39, (copy 4): p_u_40 ]]
                v_u_24.FnPostLoaded(p_u_38, p_u_39, p_u_40)
            end)
        end;
        if v_u_24.NametagPositionOffset ~= nil then
            p_u_38:set_nametag_position_offset(v_u_24.NametagPositionOffset)
        end;
        v_u_26 = v_u_4:new(p_u_17)
        v_u_27 = v_u_5:new(p_u_17, p_u_17._lobby_join:get_character_manager())
        for _, v41 in pairs(p_u_39:GetChildren()) do
            local v42 = v41:FindFirstChild(v_u_13.MoveToEnvironment) ~= nil
            local v43 = v41:FindFirstChild(v_u_13.MoveToEnvironmentNoPopper) ~= nil
            if v42 or v43 then
                if v_u_29 == nil then
                    v_u_29 = v_u_8:new()
                end;
                v_u_29:push_back(v41)
                if v42 then
                    v41.Parent = v_u_1:get_lobby_environment()
                elseif v43 then
                    v41.Parent = v_u_1:get_lobby_environment_no_popper()
                end;
            end;
        end;
        if p_u_39.PrimaryPart then
            p_u_39.PrimaryPart.Anchored = true
        end;
        if p_u_21 ~= nil then
            p_u_38:play_anim(p_u_38:load_anim(p_u_40, p_u_21))
        end;
        if v_u_24.PopupProto == nil then
            v_u_26:create_popup_on_character(game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupWebNPC, p_u_39)
        else
            v_u_26:create_popup_on_character(v_u_24.PopupProto, p_u_39)
        end;
        v_u_26:set_position_offset(p_u_38:get_nametag_position_offset() + Vector3.new(0, 0.5, 0))
        v_u_26:set_trigger_callback(function() --[[ Line: 175 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_3, (ref 3): l_TriggerPopup_0, (ref 4): v_u_15, (ref 5): p_u_22 ]]
            p_u_16._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
            l_TriggerPopup_0 = v_u_15.Dialogue
            if p_u_22 then
                p_u_22()
            end;
        end)
        v_u_27:create_popup_on_character(game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.NPCDialogueBox, p_u_39)
        v_u_28 = v_u_7:new(p_u_38:get_name(), v_u_27:get_obj().Part, v_u_27)
        v_u_2:r_set_basepart_fn(p_u_39, function(p44) --[[ Line: 186 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_1 ]]
            if v_u_2:first_child_of_type(p44, "Attachment") == nil then
                p44:SetAttribute(v_u_1:get_no_trigger_dance_sync_attribute_name(), true)
            end;
        end)
        p_u_38:update_mode()
    end, nil);
end;
return v14;
