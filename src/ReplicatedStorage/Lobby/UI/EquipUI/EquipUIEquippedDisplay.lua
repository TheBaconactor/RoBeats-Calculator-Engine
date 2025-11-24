-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:57 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_6 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_7 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_8 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.GearItemDisplay)
return {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_8, (copy 6): v_u_3, (copy 7): v_u_4, (copy 8): v_u_7 ]]
        local v14 = {}
        local v_u_15 = v_u_1:new()
        v14.cons = function(_) --[[ Name: cons ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1, (ref 3): v_u_6, (ref 4): v_u_5, (ref 5): v_u_2, (copy 6): p_u_13, (ref 7): v_u_8, (copy 8): p_u_9, (copy 9): p_u_10, (copy 10): p_u_11, (ref 11): v_u_3, (ref 12): v_u_4, (ref 13): v_u_7, (copy 14): v_u_15 ]]
            local l_CharacterSlotDisplay_0 = p_u_12.CharacterSlotDisplay
            local l_Proto_0 = l_CharacterSlotDisplay_0.Proto
            l_Proto_0.Parent = nil
            for v_u_16, v17 in v_u_1:new():add_table({
                [v_u_6.BACK] = l_CharacterSlotDisplay_0.Anchors.Back,
                [v_u_6.FACE] = l_CharacterSlotDisplay_0.Anchors.Face,
                [v_u_6.HAT] = l_CharacterSlotDisplay_0.Anchors.Hat,
                [v_u_6.NECK] = l_CharacterSlotDisplay_0.Anchors.Neck,
                [v_u_6.PANTS] = l_CharacterSlotDisplay_0.Anchors.Pants,
                [v_u_6.SHIRT] = l_CharacterSlotDisplay_0.Anchors.Shirt
            }):key_itr() do
                v_u_5:is_enum_member(v_u_16, v_u_6)
                v17.Parent = nil
                local v18 = l_Proto_0:Clone()
                v18.Parent = p_u_12
                v18:SetPrimaryPartCFrame(v17.PrimaryPart.CFrame)
                local v19 = v_u_2:new(p_u_13, p_u_12.PrimaryPart, v18.PrimaryPart)
                local v_u_20 = v_u_8:new(p_u_9, p_u_10, p_u_11, p_u_13, v19)
                v_u_20:add_child_button(p_u_13:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v19, v18.PrimaryPart, v18.RemoveButton), p_u_10, function() --[[ Line: 51 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_4, (copy 3): v_u_20, (ref 4): v_u_7, (copy 5): v_u_16, (ref 6): p_u_13 ]]
                    p_u_9._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    local v21 = v_u_20:get_displayed_ownedid()
                    v_u_7:playerblob_unequip_slot(p_u_9._player_blob_manager:get_player_blob(), v_u_16)
                    p_u_13:gear_updated_local()
                    p_u_13:update_display()
                    p_u_13:get_owned_item_display():anim_trigger_ownedid_unequipped(v21)
                end)))
                local v_u_23 = v_u_3:button_bind_anim_toggle(v_u_20:add_child_button(p_u_13:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v19, v18.PrimaryPart, v18.ToggleVisibleButton), p_u_10, function() --[[ Line: 64 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_4, (ref 3): v_u_7, (copy 4): v_u_16, (ref 5): p_u_13 ]]
                    p_u_9._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    local v22 = p_u_9._player_blob_manager:get_player_blob()
                    v_u_7:set_visible_for_slot(v22, v_u_16, not v_u_7:get_visible_for_slot(v22, v_u_16))
                    p_u_13:gear_updated_local()
                    p_u_13:update_display()
                end))), function() --[[ Line: 72 ]]
                    --[[ Upvalues: (ref 1): p_u_13 ]]
                    return p_u_13:get_alpha();
                end)
                v_u_20:set_on_display_item_playerblob_ownedid_fn(function(p24, _) --[[ Line: 73 ]]
                    --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_7, (copy 3): v_u_16 ]]
                    v_u_23:set_toggle(v_u_7:get_visible_for_slot(p24, v_u_16))
                end)
                v_u_15:add(v_u_16, v_u_20)
                v_u_20:set_empty()
                v_u_20:set_slot_icon_visible(v_u_16)
            end;
        end;
        v14.anim_trigger_slot_selected = function(_, p25) --[[ Name: anim_trigger_slot_selected ]] --[[ Line: 83 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            v_u_15:get(p25):set_scale(1.25)
        end;
        v14.update_display = function(_) --[[ Name: update_display ]] --[[ Line: 87 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_6, (copy 3): v_u_15, (ref 4): v_u_7 ]]
            local v26 = p_u_9._player_blob_manager:get_player_blob()
            for _, v27 in v_u_6:slot_itr() do
                local v28 = v_u_15:get(v27)
                local v29 = v_u_7:get_equippedobj_for_slot(v26, v27)
                if v29 == nil then
                    v28:set_empty()
                    v28:set_slot_icon_visible(v27)
                else
                    v28:set_display_item_playerblob_ownedid(v26, v29.OwnedID)
                end;
            end;
        end;
        v14.behaviour_update = function(_, p30) --[[ Name: behaviour_update ]] --[[ Line: 101 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            for _, v31 in v_u_15:key_itr() do
                v31:behaviour_update(p30)
            end;
        end;
        v14.layout = function(_) --[[ Name: layout ]] --[[ Line: 107 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            for _, v32 in v_u_15:key_itr() do
                v32:layout()
            end;
        end;
        v14:cons()
        return v14;
    end
};
