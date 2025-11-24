-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Shared.GuildRank)
local v_u_10 = require(game.ReplicatedStorage.Shared.GuildData)
require(game.ReplicatedStorage.Shared.GuildUtil)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_client(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
return {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_6, (copy 7): v_u_9, (copy 8): v_u_10, (ref 9): v_u_12, (copy 10): v_u_7, (copy 11): v_u_8 ]]
        local l__spui_0 = p_u_13._spui
        local l__menus_0 = p_u_13._menus
        local v16 = v_u_3:new(l__spui_0, l__menus_0)
        local v_u_17 = nil
        local v_u_18 = v_u_2:new()
        local v_u_19 = nil
        local v_u_20 = nil
        v16.cons = function(p_u_21) --[[ Name: cons ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_19, (ref 4): v_u_20, (copy 5): p_u_13, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): l__spui_0, (ref 9): v_u_6, (copy 10): l__menus_0, (copy 11): v_u_18, (ref 12): v_u_9 ]]
            v_u_17 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Guild.GuildMemberEditPopupUI:Clone()
            v_u_17.Name = v_u_1:gen_name(v_u_17.Name)
            p_u_21:set_showing(true)
            p_u_21._native_size = v_u_17.PrimaryPart.Size
            p_u_21._size = p_u_21._native_size
            v_u_19 = v_u_17.MainSurface.SurfaceGui.Frame.PlayerNameSection.PlayerNameDisplay
            v_u_20 = v_u_17.MainSurface.SurfaceGui.Frame.ChangeRankSection.Header
            p_u_21:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(p_u_21, v_u_17.PrimaryPart, v_u_17.BackButtonSurface), l__spui_0, function() --[[ Line: 48 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (ref 3): l__menus_0, (copy 4): p_u_21 ]]
                p_u_13._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
                l__menus_0:remove_menu(p_u_21)
            end))
            v_u_18:add(v_u_9.Owner, v_u_5:button_add_enabled_anim(p_u_21:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(p_u_21, v_u_17.PrimaryPart, v_u_17.SetRankOwner), l__spui_0, function() --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (copy 3): p_u_21, (ref 4): v_u_9 ]]
                p_u_13._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_21:set_rank_button_pressed(v_u_9.Owner)
            end)), function() --[[ Line: 63 ]]
                --[[ Upvalues: (copy 1): p_u_21 ]]
                return p_u_21:get_alpha();
            end))
            v_u_18:add(v_u_9.Admin, v_u_5:button_add_enabled_anim(p_u_21:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(p_u_21, v_u_17.PrimaryPart, v_u_17.SetRankAdmin), l__spui_0, function() --[[ Line: 70 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (copy 3): p_u_21, (ref 4): v_u_9 ]]
                p_u_13._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_21:set_rank_button_pressed(v_u_9.Admin)
            end)), function() --[[ Line: 75 ]]
                --[[ Upvalues: (copy 1): p_u_21 ]]
                return p_u_21:get_alpha();
            end))
            v_u_18:add(v_u_9.Member, v_u_5:button_add_enabled_anim(p_u_21:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(p_u_21, v_u_17.PrimaryPart, v_u_17.SetRankMember), l__spui_0, function() --[[ Line: 82 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (copy 3): p_u_21, (ref 4): v_u_9 ]]
                p_u_13._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_21:set_rank_button_pressed(v_u_9.Member)
            end)), function() --[[ Line: 87 ]]
                --[[ Upvalues: (copy 1): p_u_21 ]]
                return p_u_21:get_alpha();
            end))
            p_u_21:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(p_u_21, v_u_17.PrimaryPart, v_u_17.KickButton), l__spui_0, function() --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (copy 3): p_u_21 ]]
                p_u_13._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_21:kick_button_pressed()
            end))
            p_u_21:update_display()
            p_u_21:transition_update_visual(0)
            p_u_21:layout()
        end;
        v16.update_display = function(_) --[[ Name: update_display ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): p_u_15, (ref 3): v_u_20, (ref 4): v_u_1, (ref 5): v_u_9, (copy 6): p_u_14, (ref 7): v_u_10, (copy 8): v_u_18 ]]
            v_u_19.Text = p_u_15:get_name()
            v_u_20.Text = string.format("Change Member Rank (%s)", v_u_1:enum_val_to_name(p_u_15:get_rank(), v_u_9))
            local v22 = v_u_10:get_player_info(p_u_14:get_guild_data(), v_u_1:get_local_userid()):get_rank()
            local v23 = p_u_15:get_rank()
            if p_u_15:get_rbxid() == v_u_1:get_local_userid() then
                for _, v24 in v_u_18:key_itr() do
                    v24:set_enabled(false)
                end;
            else
                for v25, v26 in v_u_18:key_itr() do
                    local v27 = v_u_9:can_set_rank(v22, v23, v25)
                    if v27 then
                        v27 = v25 ~= p_u_15:get_rank()
                    end;
                    v26:set_enabled(v27)
                end;
            end;
        end;
        v16.set_rank_button_pressed = function(p_u_28, p_u_29) --[[ Name: set_rank_button_pressed ]] --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): p_u_13, (ref 5): v_u_12, (copy 6): l__spui_0, (ref 7): v_u_7, (copy 8): p_u_14, (ref 9): v_u_10 ]]
            p_u_13._menus:push_menu(v_u_12:new(p_u_13, l__spui_0, p_u_13._menus):set_text("Confirm Change Rank", (string.format("Are you sure you want to change the rank of \"%s\" to %s?", p_u_15:get_name(), v_u_1:enum_val_to_name(p_u_29, v_u_9)))):set_okay_button_fn(function() --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_12, (ref 3): v_u_7, (ref 4): p_u_14, (ref 5): p_u_15, (ref 6): v_u_10, (copy 7): p_u_28, (copy 8): p_u_29 ]]
                local v_u_30 = p_u_13._menus:push_menu(v_u_12:new(p_u_13, p_u_13._spui, p_u_13._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_13._evt:wait_on_event_once(v_u_7.EVT_Guild_EditPlayerRank_ServerResponse, function(p31, _, p32) --[[ Line: 129 ]]
                    --[[ Upvalues: (ref 1): p_u_14, (ref 2): p_u_15, (ref 3): v_u_10, (ref 4): p_u_13, (copy 5): v_u_30, (ref 6): p_u_28 ]]
                    if p31 then
                        p_u_14:set_guild_data_from_tab(p32)
                        p_u_15 = v_u_10:get_player_info(p_u_14:get_guild_data(), p_u_15:get_rbxid())
                    end;
                    p_u_13._menus:remove_menu(v_u_30)
                    p_u_28:update_display()
                end)
                p_u_13._evt:fire_event_to_server(v_u_7.EVT_Guild_EditPlayerRank_Client, p_u_15:get_rbxid(), p_u_29)
            end))
        end;
        v16.kick_button_pressed = function(p_u_33) --[[ Name: kick_button_pressed ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): p_u_15, (copy 2): p_u_13, (ref 3): v_u_12, (copy 4): l__spui_0, (ref 5): v_u_7, (copy 6): p_u_14, (copy 7): l__menus_0 ]]
            p_u_13._menus:push_menu(v_u_12:new(p_u_13, l__spui_0, p_u_13._menus):set_text("Confirm Kick", (string.format("Are you sure you want to remove \"%s\" from the Team?", p_u_15:get_name()))):set_okay_button_fn(function() --[[ Line: 143 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_12, (ref 3): v_u_7, (ref 4): p_u_14, (ref 5): l__menus_0, (copy 6): p_u_33, (ref 7): p_u_15 ]]
                local v_u_34 = p_u_13._menus:push_menu(v_u_12:new(p_u_13, p_u_13._spui, p_u_13._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_13._evt:wait_on_event_once(v_u_7.EVT_Guild_KickPlayer_ServerResponse, function(p35, _, p36) --[[ Line: 145 ]]
                    --[[ Upvalues: (ref 1): p_u_14, (ref 2): l__menus_0, (copy 3): v_u_34, (ref 4): p_u_33 ]]
                    if p35 then
                        p_u_14:set_guild_data_from_tab(p36)
                    end;
                    l__menus_0:remove_menu(v_u_34)
                    l__menus_0:remove_menu(p_u_33)
                end)
                p_u_13._evt:fire_event_to_server(v_u_7.EVT_Guild_KickPlayer_Client, p_u_15:get_rbxid())
            end))
        end;
        v16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:Destroy()
        end;
        local v_u_37 = 1
        local v_u_38 = 1
        v16.layout = function(p39) --[[ Name: layout ]] --[[ Line: 162 ]]
            --[[ Upvalues: (copy 1): l__spui_0, (ref 2): v_u_38, (ref 3): v_u_17 ]]
            p39:opt_rescale_to_max_nxy(l__spui_0, 0.8, 0.8, v_u_38)
            local v40, v41 = p39:opt_update_cframe_params(l__spui_0, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p39:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v40 == true then
                v_u_17:SetPrimaryPartCFrame(v41)
            end;
        end;
        v16.set_alpha = function(_, p42) --[[ Name: set_alpha ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_1, (ref 3): v_u_17 ]]
            if v_u_37 ~= p42 then
                v_u_37 = p42
                v_u_1:r_set_alpha(v_u_17, v_u_37)
            end;
        end;
        v16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v16.set_scale = function(_, p43) --[[ Name: set_scale ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            v_u_38 = p43
        end;
        v16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            return v_u_38;
        end;
        v16.get_native_size = function(p44) --[[ Name: get_native_size ]] --[[ Line: 184 ]]
            return p44._native_size;
        end;
        v16.get_size = function(p45) --[[ Name: get_size ]] --[[ Line: 187 ]]
            return p45._size;
        end;
        v16.set_size = function(p46, p47) --[[ Name: set_size ]] --[[ Line: 190 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            p46._size = p47
            v_u_17.PrimaryPart.Size = Vector3.new(p47.X, p47.Y, 0)
        end;
        v16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.Position;
        end;
        v16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.SurfaceGui;
        end;
        v16.set_showing = function(_, p48) --[[ Name: set_showing ]] --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_8 ]]
            if p48 then
                v_u_17.Parent = v_u_8:get_world_ui_folder()
            else
                v_u_17.Parent = nil
            end;
        end;
        v16:cons()
        return v16;
    end
};
