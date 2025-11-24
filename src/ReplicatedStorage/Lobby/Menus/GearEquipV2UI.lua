-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_7 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2UI_EquippedSection)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2UI_OwnedSection)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2UI_StatsSection)
return {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8, (copy 3): v_u_9, (copy 4): v_u_1, (copy 5): v_u_6, (copy 6): v_u_3, (copy 7): v_u_10, (copy 8): v_u_11, (copy 9): v_u_12, (copy 10): v_u_5, (copy 11): v_u_4, (copy 12): v_u_7 ]]
        local v16 = v_u_2:new(p_u_14, p_u_15)
        local v_u_17 = nil
        local v_u_18 = 1
        local v_u_19 = 1
        local v_u_20 = nil
        v16.get_equipped_section = function(_) --[[ Name: get_equipped_section ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local function f_get_equipdict() --[[ Name: get_equipdict ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_8, (ref 3): v_u_9 ]]
            local v24 = p_u_13._player_blob_manager:get_player_blob()
            local v25 = {}
            for _, v26 in v_u_8:slot_itr() do
                local v27 = 0
                local v28 = v_u_9:get_equippedobj_for_slot(v24, v26)
                local v29, v30
                if v28 == nil then
                    v29 = -1
                    v30 = ""
                else
                    v29 = v28.OwnedID
                    v30 = v_u_9:get_equipmentdata_for_slot(v24, v26):get_name()
                    if v_u_9:get_visible_for_slot(v24, v26) == true then
                        v27 = true
                    end;
                end;
                v25[v26] = {
                    ["OwnedID"] = v29,
                    ["EquipmentName"] = v30,
                    ["Visible"] = v27
                }
            end;
            return v25;
        end;
        local function f_cmp_equipdicts(p31, p32) --[[ Name: cmp_equipdicts ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            for _, v33 in v_u_8:slot_itr() do
                local v34 = p31[v33]
                local v35 = p32[v33]
                if v34.OwnedID ~= v35.OwnedID or (v34.EquipmentName ~= v35.EquipmentName or v34.Visible ~= v35.Visible) then
                    return false;
                end;
            end;
            return true;
        end;
        v16.cons = function(p36) --[[ Name: cons ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_6, (copy 4): p_u_14, (copy 5): p_u_13, (ref 6): v_u_3, (ref 7): v_u_23, (copy 8): f_get_equipdict, (ref 9): v_u_20, (ref 10): v_u_10, (ref 11): v_u_21, (ref 12): v_u_11, (ref 13): v_u_22, (ref 14): v_u_12 ]]
            v_u_17 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.GearEquipV2UI:Clone()
            v_u_17.Name = v_u_1:gen_name(v_u_17.Name)
            v_u_17.Parent = v_u_6:get_world_ui_folder()
            p36._native_size = p_u_14:get_size_from_nxy(1, 1)
            p36._size = p36._native_size
            local v_u_37 = nil
            pcall(function() --[[ Line: 81 ]]
                --[[ Upvalues: (ref 1): v_u_37, (ref 2): p_u_13 ]]
                v_u_37 = p_u_13:get_local_character().PrimaryPart.CFrame
            end)
            if v_u_37 == nil then
                v_u_37 = game.Workspace.CurrentCamera.CFrame
            end;
            p_u_13:transition_local_camera_cframe(CFrame.new(v_u_37.p + v_u_37.lookVector * 8 + Vector3.new(0, 2.5, 0), v_u_37.p))
            if p_u_13._player_blob_manager:is_synced() == false then
                p_u_13._player_blob_manager:do_sync()
                v_u_3:warnf("GearEquipUI player_blob sync")
            end;
            v_u_23 = f_get_equipdict()
            v_u_20 = v_u_10:new(p_u_13, p_u_14, p36, v_u_17.Equipped)
            v_u_21 = v_u_11:new(p_u_13, p_u_14, p36, v_u_17.Owned)
            v_u_22 = v_u_12:new(p_u_13, p_u_14, p36, v_u_17.Stats)
            p36:refresh_ui()
            p36:reset_selected_item()
            p36:transition_update_visual(0)
            p36:layout()
        end;
        v16.gear_updated_local = function(_) --[[ Name: gear_updated_local ]] --[[ Line: 109 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_5, (ref 3): v_u_3 ]]
            local v38 = p_u_13._player_blob_manager:get_player_blob()
            p_u_13._evt:wait_on_event_once(v_u_5.EVT_Lobby_ServerAcknowledgeCharacterUpdateEquipped, function(p39, p40) --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                if p39 == false then
                    v_u_3:errf(p40)
                end;
            end)
            p_u_13._evt:fire_event_to_server(v_u_5.EVT_Lobby_ClientNotifyCharacterUpdateEquipped, v38.Equipped, {}, {}, false)
        end;
        v16.back_action = function(p41) --[[ Name: back_action ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_15, (copy 4): f_get_equipdict, (copy 5): f_cmp_equipdicts, (ref 6): v_u_23, (ref 7): v_u_7, (copy 8): p_u_14, (ref 9): v_u_5 ]]
            p_u_13._sfx_manager:play_sfx(v_u_4.SFX_MENU_CLOSE)
            p_u_15:remove_menu(p41)
            if f_cmp_equipdicts(f_get_equipdict(), v_u_23) ~= true then
                local v_u_42 = p_u_15:push_menu(v_u_7:new(p_u_13, p_u_14, p_u_15):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
                local v43 = p_u_13._player_blob_manager:get_player_blob()
                p_u_13._evt:wait_on_event_once(v_u_5.EVT_Lobby_ServerAcknowledgeCharacterUpdateEquipped, function(p_u_44, p_u_45) --[[ Line: 130 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_15, (copy 3): v_u_42, (ref 4): v_u_7, (ref 5): p_u_14 ]]
                    p_u_13._player_blob_manager:do_sync(function(_) --[[ Line: 131 ]]
                        --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_42, (copy 3): p_u_44, (ref 4): v_u_7, (ref 5): p_u_13, (ref 6): p_u_14, (copy 7): p_u_45 ]]
                        p_u_15:remove_menu(v_u_42)
                        if p_u_44 == false then
                            p_u_15:push_menu(v_u_7:new(p_u_13, p_u_14, p_u_15):set_text("Error", p_u_45))
                        end;
                    end)
                end)
                p_u_13._evt:fire_event_to_server(v_u_5.EVT_Lobby_ClientNotifyCharacterUpdateEquipped, v43.Equipped, {}, {}, true)
            end;
        end;
        v16.refresh_ui = function(_) --[[ Name: refresh_ui ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (ref 3): v_u_22 ]]
            v_u_20:refresh_ui()
            v_u_21:refresh_ui()
            v_u_22:refresh_ui()
        end;
        v16.visual_update = function(p46, p47, p48) --[[ Name: visual_update ]] --[[ Line: 147 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_20, (ref 3): v_u_21 ]]
            if p_u_13:transition_local_camera_cframe_finished() ~= false and p_u_13._player_blob_manager:is_synced() ~= false then
                v_u_20:visual_update(p47, p48)
                v_u_21:visual_update(p47, p48)
                p46:visual_update_base(p47, p48)
            end;
        end;
        v16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:Destroy()
        end;
        v16.layout = function(p49) --[[ Name: layout ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_17, (copy 2): p_u_14, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22 ]]
            v_u_17.PrimaryPart.Size = Vector3.new(p_u_14:get_size_from_nxy(1, 1).X, p_u_14:get_size_from_nxy(1, 1).Y, 0)
            p49._size = v_u_17.PrimaryPart.Size
            v_u_17.PrimaryPart.CFrame = p_u_14:get_cframe()
            v_u_20:layout()
            v_u_21:layout()
            v_u_22:layout()
        end;
        v16.set_alpha = function(_, p50) --[[ Name: set_alpha ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1, (ref 3): v_u_17 ]]
            if v_u_18 ~= p50 then
                v_u_18 = p50
                v_u_1:r_set_alpha(v_u_17, v_u_18)
            end;
        end;
        v16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v16.set_scale = function(_, p51) --[[ Name: set_scale ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_21, (ref 4): v_u_22 ]]
            v_u_19 = p51
            v_u_20:set_scale(p51)
            v_u_21:set_scale(p51)
            v_u_22:set_scale(p51)
        end;
        v16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v16.get_native_size = function(p52) --[[ Name: get_native_size ]] --[[ Line: 188 ]]
            return p52._native_size;
        end;
        v16.get_size = function(p53) --[[ Name: get_size ]] --[[ Line: 191 ]]
            return p53._size;
        end;
        v16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.Position;
        end;
        v16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.SurfaceGui;
        end;
        v16:cons()
        return v16;
    end
};
