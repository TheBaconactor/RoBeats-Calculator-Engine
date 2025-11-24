-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_9 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.CharacterDisplaySection)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Pets.PetInfoBase)
require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() end)
return {
    ["new"] = function(_, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_6, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_7, (copy 8): v_u_9, (copy 9): v_u_8 ]]
        local v_u_14 = v_u_3:new(p_u_11, p_u_12)
        local v_u_15 = nil
        local v_u_16 = 1
        local v_u_17 = 1
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        v_u_14.get_character_display = function(_) --[[ Name: get_character_display ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        local v_u_22 = v_u_2:new()
        v_u_14.get_action_buttons = function(_) --[[ Name: get_action_buttons ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_22 ]]
            return v_u_22;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_6, (copy 4): v_u_14, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_20, (copy 8): p_u_10, (ref 9): v_u_5, (ref 10): v_u_4, (copy 11): p_u_11, (ref 12): v_u_7, (copy 13): p_u_12, (ref 14): p_u_13, (ref 15): v_u_9, (ref 16): v_u_21, (ref 17): v_u_2, (copy 18): v_u_22 ]]
            v_u_15 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.PreviewCharacterUI:Clone()
            v_u_15.Name = v_u_1:gen_name(v_u_15.Name)
            v_u_15.Parent = v_u_6:get_world_ui_folder()
            v_u_14._native_size = v_u_15.PrimaryPart.Size
            v_u_14._size = v_u_14._native_size
            v_u_18 = v_u_15.MainSurface.SurfaceGui.Frame
            v_u_19 = v_u_18.TextSection.NameDisplay
            v_u_20 = v_u_18.TextSection.DescriptionDisplay
            v_u_19.Text = ""
            v_u_20.Text = ""
            v_u_14:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(v_u_14, v_u_15.PrimaryPart, v_u_15.BackButtonSurface), p_u_11, function() --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_7, (ref 3): p_u_12, (ref 4): v_u_14 ]]
                p_u_10._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
                p_u_12:remove_menu(v_u_14)
            end))
            if p_u_13 == nil then
                p_u_13 = v_u_9.Config:new()
                p_u_13.LoadLocalUser = true
                p_u_13.CycleOwnedDancesOnClick = false
                p_u_13.FillDanceListWithOwnedDances = false
            end;
            v_u_21 = v_u_9:new(p_u_10, p_u_11, v_u_4:new(v_u_14, v_u_15.PrimaryPart, v_u_15.RenderCharacterSurface), v_u_15.RenderCharacterSurface.SurfaceGui, p_u_13)
            for _, v23 in v_u_2:new({ v_u_15.Buttons.Button1, v_u_15.Buttons.Button2, v_u_15.Buttons.Button3 }):key_itr() do
                local v_u_24 = nil
                v_u_24 = v_u_14:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(v_u_14, v_u_15.PrimaryPart, v23), p_u_11, function() --[[ Line: 93 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_7, (ref 3): v_u_24 ]]
                    p_u_10._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                    if v_u_24:get_bound_data() ~= nil then
                        v_u_24:get_bound_data()()
                    end;
                end))
                v_u_24:set_visible(false)
                v_u_22:push_back(v_u_24)
            end;
        end;
        v_u_14.set_text = function(p25, p26, p27) --[[ Name: set_text ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20 ]]
            v_u_19.Text = p26
            v_u_20.Text = p27
            return p25;
        end;
        v_u_14.layout = function(p28) --[[ Name: layout ]] --[[ Line: 111 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_17, (ref 3): v_u_15, (ref 4): v_u_21 ]]
            p28:opt_rescale_to_max_nxy(p_u_11, 0.8, 0.8, v_u_17)
            local v29, v30 = p28:opt_update_cframe_params(p_u_11, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p28:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v29 == true then
                v_u_15:SetPrimaryPartCFrame(v30)
            end;
            v_u_21:layout()
        end;
        v_u_14.visual_update = function(p31, p32, p33) --[[ Name: visual_update ]] --[[ Line: 125 ]]
            p31:visual_update_base(p32, p33)
        end;
        v_u_14.behaviour_update = function(p34, p35) --[[ Name: behaviour_update ]] --[[ Line: 129 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_8, (ref 3): v_u_21 ]]
            p34:behaviour_update_base(p35, p_u_10)
            if p34._current_mode == v_u_8.MODE_OPEN then
                v_u_21:behaviour_update(p35)
            end;
        end;
        local v_u_36 = nil
        v_u_14.set_fn_on_remove = function(p37, p38) --[[ Name: set_fn_on_remove ]] --[[ Line: 137 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            v_u_36 = p38
            return p37;
        end;
        v_u_14.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_15, (ref 3): v_u_21 ]]
            if v_u_36 then
                v_u_36()
            end;
            v_u_15:Destroy()
            v_u_21:teardown()
        end;
        v_u_14.set_alpha = function(_, p39) --[[ Name: set_alpha ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_1, (ref 3): v_u_15, (ref 4): v_u_21 ]]
            if v_u_16 ~= p39 then
                v_u_16 = p39
                v_u_1:r_set_alpha(v_u_15, v_u_16)
                v_u_21:set_alpha(v_u_16)
            end;
        end;
        v_u_14.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        v_u_14.set_scale = function(_, p40) --[[ Name: set_scale ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = p40
        end;
        v_u_14.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v_u_14.get_native_size = function(p41) --[[ Name: get_native_size ]] --[[ Line: 159 ]]
            return p41._native_size;
        end;
        v_u_14.get_size = function(p42) --[[ Name: get_size ]] --[[ Line: 162 ]]
            return p42._size;
        end;
        v_u_14.set_size = function(p43, p44) --[[ Name: set_size ]] --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            p43._size = p44
            v_u_15.PrimaryPart.Size = Vector3.new(p44.X, p44.Y, 0)
        end;
        v_u_14.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 169 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.PrimaryPart.Position;
        end;
        v_u_14.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 172 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.PrimaryPart.SurfaceGui;
        end;
        v_u_14.set_showing = function(_, p45) --[[ Name: set_showing ]] --[[ Line: 175 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_6 ]]
            if p45 then
                v_u_15.Parent = v_u_6:get_world_ui_folder()
            else
                v_u_15.Parent = nil
            end;
        end;
        f_cons()
        return v_u_14;
    end
};
