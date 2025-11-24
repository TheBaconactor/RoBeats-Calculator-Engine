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
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_6 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.GearItemDisplay)
return {
    ["new"] = function(_, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_6, (copy 5): v_u_3, (copy 6): v_u_4 ]]
        local v12 = {}
        local v_u_13 = v_u_1:new()
        v12.cons = function(_) --[[ Name: cons ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_1, (ref 3): v_u_5, (ref 4): v_u_2, (copy 5): p_u_11, (ref 6): v_u_6, (copy 7): p_u_7, (copy 8): p_u_8, (copy 9): p_u_9, (ref 10): v_u_3, (ref 11): v_u_4, (copy 12): v_u_13 ]]
            local l_PetDisplay_0 = p_u_10.PetDisplay
            local l_Proto_0 = l_PetDisplay_0.Proto
            l_Proto_0.Parent = nil
            for v_u_14, v15 in v_u_1:new():add_table({
                [v_u_5:get_pet_slot_1_id()] = l_PetDisplay_0.Anchors.PetSlot1,
                [v_u_5:get_pet_slot_2_id()] = l_PetDisplay_0.Anchors.PetSlot2,
                [v_u_5:get_pet_slot_3_id()] = l_PetDisplay_0.Anchors.PetSlot3
            }):key_itr() do
                v15.Parent = nil
                local v16 = l_Proto_0:Clone()
                v16.Parent = p_u_10
                v16:SetPrimaryPartCFrame(v15.PrimaryPart.CFrame)
                local v17 = v_u_2:new(p_u_11, p_u_10.PrimaryPart, v16.PrimaryPart)
                local v_u_18 = v_u_6:new(p_u_7, p_u_8, p_u_9, p_u_11, v17)
                v_u_18:add_child_button(p_u_11:add_cycle_element(p_u_7, 1, v_u_3:new(v_u_2:new(v17, v16.PrimaryPart, v16.RemoveButton), p_u_8, function() --[[ Line: 47 ]]
                    --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_4, (copy 3): v_u_18, (ref 4): v_u_5, (copy 5): v_u_14, (ref 6): p_u_11 ]]
                    p_u_7._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    local v19 = v_u_18:get_displayed_pet_ownedid()
                    v_u_5:playerblob_remove_pet_slotid(p_u_7._player_blob_manager:get_player_blob(), v_u_14)
                    p_u_11:gear_updated_local()
                    p_u_11:update_display()
                    p_u_11:get_owned_item_display():anim_trigger_pet_ownedid_unequipped(v19)
                end)))
                v_u_13:add(v_u_14, v_u_18)
                v_u_18:set_empty()
                v_u_18:set_slot_icon_visible_pet()
            end;
        end;
        v12.anim_trigger_slot_selected = function(_, p20) --[[ Name: anim_trigger_slot_selected ]] --[[ Line: 65 ]]
            --[[ Upvalues: (copy 1): v_u_13 ]]
            v_u_13:get(p20):set_scale(1.25)
        end;
        v12.update_display = function(_) --[[ Name: update_display ]] --[[ Line: 69 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_5, (copy 3): v_u_13 ]]
            local v21 = p_u_7._player_blob_manager:get_player_blob()
            local v22 = v_u_5:playerblob_get_slot_to_owned_pet_dict(v21)
            for v23, v24 in v_u_13:key_itr() do
                if v22:contains(v23) then
                    v24:set_display_item_playerblob_pet_ownedid(v21, (v_u_5:ownedpet_get_ownedid(v22:get(v23))))
                else
                    v24:set_empty()
                    v24:set_slot_icon_visible_pet()
                end;
            end;
        end;
        v12.behaviour_update = function(_, p25) --[[ Name: behaviour_update ]] --[[ Line: 84 ]]
            --[[ Upvalues: (copy 1): v_u_13 ]]
            for _, v26 in v_u_13:key_itr() do
                v26:behaviour_update(p25)
            end;
        end;
        v12.layout = function(_) --[[ Name: layout ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): v_u_13 ]]
            for _, v27 in v_u_13:key_itr() do
                v27:layout()
            end;
        end;
        v12:cons()
        return v12;
    end
};
