-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_4 = {
    ["Mode"] = {
        ["NotLoaded"] = 1,
        ["TransitionIn"] = 2,
        ["Loaded"] = 3,
        ["TransitionOut"] = 4
    }
}
v_u_4.new = function(_, p_u_5, p6, p7) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_1 ]]
    local v8 = {}
    Vector3.new()
    Vector3.new()
    p_u_5.Parent = p7
    local v_u_9 = v_u_3:new(p6, p7, p_u_5)
    local l_NotLoaded_0 = v_u_4.Mode.NotLoaded
    local v_u_10 = 0
    local v_u_11 = 1
    local v_u_12 = -1
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    v8.cons = function(_) --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): p_u_5, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_18 ]]
        local l_Frame_0 = p_u_5.SurfaceGui.Frame
        v_u_13 = l_Frame_0.Frame
        v_u_14 = l_Frame_0.IconBack
        v_u_15 = l_Frame_0.IconBack.Icon
        v_u_16 = l_Frame_0.NameDisplay
        v_u_17 = l_Frame_0.SubDisplay
        v_u_18 = l_Frame_0.ModeDisplay
    end;
    v8.visual_update = function(p19, p20, _) --[[ Name: visual_update ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_4, (ref 3): v_u_10, (ref 4): v_u_2, (copy 5): v_u_9, (ref 6): v_u_11 ]]
        if l_NotLoaded_0 == v_u_4.Mode.NotLoaded then
            p19:set_alpha(0)
        elseif l_NotLoaded_0 == v_u_4.Mode.TransitionIn then
            v_u_10 = v_u_10 + v_u_2:sec_to_tick(0.25) * p20
            local l_Y_0 = v_u_2:BezierPt2ForT(0, 0, 0, 0.5, 0.5, 1, 1, 1, v_u_10).Y
            p19:set_scale(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1.25), Vector2.new(1, 1), l_Y_0))
            p19:set_alpha(v_u_2:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(1, 1), l_Y_0))
            if v_u_10 >= 1 then
                l_NotLoaded_0 = v_u_4.Mode.Loaded
            end;
        elseif l_NotLoaded_0 == v_u_4.Mode.Loaded then
            p19:set_alpha(1)
        elseif l_NotLoaded_0 == v_u_4.Mode.TransitionOut then
            v_u_10 = v_u_10 + v_u_2:sec_to_tick(0.25) * p20
            local l_Y_1 = v_u_2:BezierPt2ForT(0, 0, 0, 0.5, 0.5, 1, 1, 1, v_u_10).Y
            local v21 = v_u_2:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 0), l_Y_1)
            p19:set_scale(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 0.5), l_Y_1))
            p19:set_alpha(v21)
            if v_u_10 >= 1 then
                l_NotLoaded_0 = v_u_4.Mode.NotLoaded
            end;
        end;
        v_u_9:set_scale(v_u_11)
        v_u_9:layout()
    end;
    v8.set_loaded = function(p22, p23) --[[ Name: set_loaded ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_4, (ref 3): v_u_10 ]]
        if p23 == true then
            if l_NotLoaded_0 == v_u_4.Mode.NotLoaded or l_NotLoaded_0 == v_u_4.Mode.TransitionOut then
                l_NotLoaded_0 = v_u_4.Mode.TransitionIn
                v_u_10 = 0
                return;
            end;
        else
            if l_NotLoaded_0 == v_u_4.Mode.Loaded or l_NotLoaded_0 == v_u_4.Mode.TransitionIn then
                l_NotLoaded_0 = v_u_4.Mode.TransitionOut
                v_u_10 = 0
                return;
            end;
            p22:set_alpha(0)
        end;
    end;
    v8.set_scale = function(_, p24) --[[ Name: set_scale ]] --[[ Line: 103 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        v_u_11 = p24
    end;
    v8.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 104 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        return v_u_9:get_scale();
    end;
    v8.set_position = function(_, p25) --[[ Name: set_position ]] --[[ Line: 106 ]]
        --[[ Upvalues: (copy 1): p_u_5, (copy 2): v_u_9 ]]
        p_u_5.Position = p25
        v_u_9:update_basis_offset()
    end;
    v8.set_visible = function(_, p26) --[[ Name: set_visible ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): p_u_5 ]]
        p_u_5.SurfaceGui.Enabled = p26
    end;
    v8.set_game_instance_player = function(_, p27) --[[ Name: set_game_instance_player ]] --[[ Line: 113 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_15, (ref 4): v_u_18 ]]
        v_u_16.Text = p27._name
        v_u_17.Text = ""
        v_u_15.Image = string.format("https://www.roblox.com/headshot-thumbnail/image?userId=%d&width=150&height=150&format=png", p27._id)
        v_u_18.Visible = false
    end;
    v8.sub_display_loaded_or_timeout = function(_, p28) --[[ Name: sub_display_loaded_or_timeout ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        if p28._loaded == true then
            v_u_17.Text = "Loaded!"
        else
            v_u_17.Text = string.format("Loading (%d)...", (math.floor(p28._timeout / 1000)))
        end;
    end;
    v8.set_alpha = function(p29, p30) --[[ Name: set_alpha ]] --[[ Line: 137 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_1, (copy 3): p_u_5 ]]
        if v_u_12 == p30 then
            return p29;
        end;
        v_u_12 = p30
        v_u_1:obj_set_alpha(p_u_5, v_u_12, 1)
        return p29;
    end;
    v8.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        return v_u_12;
    end;
    v8:cons()
    return v8;
end;
return v_u_4;
