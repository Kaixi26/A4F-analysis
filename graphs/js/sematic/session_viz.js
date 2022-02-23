
session_viz = {}

session_viz.start = (data) => {

    cmdKeys = Object.keys(data["cmds"])
    cmdKeys.forEach(key => {
        var button = document.createElement("BUTTON");
        button.innerHTML = key;
        button.onclick = () => reload(key)
        document.getElementById("keys").appendChild(button)
    })


    function reload(cmdKey, hide_below) {
        document.getElementById("min-filter").oninput = e => {
            reload(cmdKey, e.target.value || 0)
        }

        node_color = group => (group === 1 && "#0000FF") || (group === 0 && "#00FF00") || "#FF0000"
        node_color_hid = group => (group === 1 && "#0000FF55") || (group === 0 && "#00FF0055") || "#FF000055"

        edge_color = group => (group === 1 && "#0000AA") || (group === 0 && "#00AA00") || "#AA0000"
        edge_color_hid = group => (group === 1 && "#0000AA55") || (group === 0 && "#00AA0055") || "#AA000055"

        var nodes = data.cmds[cmdKey].nodes.map((x, id) => ({
            ...x,
            id,
            value: x.ids.length,
            total: x.ids.length,
            group: (data.execution_info[x.ids[0]] ?? {"sat": 1}).sat,
            color: node_color((data.execution_info[x.ids[0]] ?? {"sat": 1}).sat),
        })).filter(x => x.total >= hide_below)

        var edges = Object.entries(data.cmds[cmdKey].edges)
            .flatMap(([from, tos]) => {
                return Object.entries(tos).map(([to, info]) => {
                    return {
                        ...info,
                        from: parseInt(from),
                        to: parseInt(to),
                        arrows: "to",
                        value: info.ids.length,
                        total: info.ids.length,
                        group: 1,
                        color: edge_color(1),
                    }
                })
            }).filter(x => x.total >= hide_below)

        var nodesDataset = new vis.DataSet(nodes);
        var edgesDataset = new vis.DataSet(edges);
        setInfo = (str) => document.getElementById('info').innerHTML = str

        highlightOnNode = (selected) => {

            nodes = nodes.map((x, i) => ({
                ...x,
                color: i == selected ? node_color(x.group) : node_color_hid(x.group),
            }))
            edges = edges.map(x => ({
                ...x,
                color: x.to === selected || x.from === selected ? edge_color(x.group) : edge_color_hid(x.group),
            }))

            document.getElementById("extras").innerHTML = ""
            nodes[selected].ids.forEach(id => {
                if(id === "") return
                div = document.createElement("div")
                div.innerHTML = id
                div.onclick = () => setInfo(`code for id ${id}\n\n${data.execution_info[id].code_stripped}`)
                document.getElementById("extras").appendChild(div)
            })

            setInfo(`total: ${nodes[selected].total}`)

            nodesDataset.update(nodes)
            edgesDataset.update(edges)
        }

        highlightOnEdge = (selected) => {
            const { from, to } = edges.find(({ id }) => id === selected)
            const edge = edges.find(e => e.from === from && e.to === to)

            nodes = nodes.map((x, i) => ({
                ...x,
                color: i === from || i === to ? edge_color(x.group) : edge_color_hid(x.group),
            }))
            edges = edges.map((x, i) => ({
                ...x,
                color: x.from === from && x.to === to ? edge_color(x.group) : edge_color_hid(x.group),
            }))

            document.getElementById("extras").innerHTML = ""
            edge.ids.forEach(({ from, to }) => {
                div = document.createElement("div")
                div.innerHTML = `${from}->${to}`
                div.onclick = () => setInfo(`\
from id ${from}\n
${from && data.execution_info[from].code_stripped}\n--------
to id ${to}\n
${to && data.execution_info[to].code_stripped}
`)
                document.getElementById("extras").appendChild(div)
            })

            setInfo(`total: ${edge.total}`)

            nodesDataset.update(nodes)
            edgesDataset.update(edges)
        }

        highlightOff = () => {
            document.getElementById("extras").innerHTML = ""
            nodes = nodes.map(x => ({
                ...x,
                color: node_color(x.group),
            }))
            edges = edges.map(x => ({
                ...x,
                color: edge_color(x.group),
            }))

            nodesDataset.update(nodes)
            edgesDataset.update(edges)
        }

        highlightHandler = (params) => {
            highlightOff(params)
            if (params.nodes.length > 0)
                highlightOnNode(params.nodes[0])
            else if (params.edges.length > 0)
                highlightOnEdge(params.edges[0])
        }

        draw = (nodes, edges) => {
            var container = document.getElementById('network');
            var data = {
                nodes: nodesDataset,
                edges: edgesDataset
            };
            var options = {
                nodes: {
                    shape: "dot"
                },
                physics: {
                    stabilization: false,
                },
            }
            var network = new vis.Network(container, data, options);
            network.on("click", highlightHandler);
        }

        draw(nodes, edges)
    }

    reload(cmdKeys[0], 0)
}
